"""
Upload queue service for sequential photo uploads to Google Drive.

This prevents race conditions that cause duplicate folders when
multiple photos are uploaded concurrently.
"""
import asyncio
import os
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

from services.drive_service import get_drive_service, UploadResult

logger = logging.getLogger(__name__)


@dataclass
class UploadTask:
    """A single upload task in the queue."""
    bot: any
    chat_id: int
    photo_file_id: str
    local_path: str
    drive_folder: str
    user_id: int
    photo_num: int
    lang: str
    on_success: Optional[Callable[[], Awaitable[None]]] = None
    on_failure: Optional[Callable[[str], Awaitable[None]]] = None


class UploadQueue:
    """
    Singleton upload queue that processes photos sequentially.
    
    This ensures folders are created only once and photos are uploaded
    one at a time to prevent race conditions.
    """
    
    _instance: Optional['UploadQueue'] = None
    
    def __new__(cls) -> 'UploadQueue':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._queue: asyncio.Queue[UploadTask] = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._initialized = True
        logger.info("Upload queue initialized")
    
    def start(self):
        """Start the queue worker if not already running."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Upload queue worker started")
    
    async def stop(self):
        """Stop the queue worker gracefully."""
        self._is_running = False
        if self._worker_task:
            # Put a None to signal shutdown
            await self._queue.put(None)
            await self._worker_task
            self._worker_task = None
            logger.info("Upload queue worker stopped")
    
    async def add_task(self, task: UploadTask):
        """Add an upload task to the queue."""
        # Ensure worker is running
        self.start()
        await self._queue.put(task)
        queue_size = self._queue.qsize()
        logger.info(f"[Photo #{task.photo_num}] Added to queue (queue size: {queue_size})")
    
    async def _worker(self):
        """Background worker that processes upload tasks sequentially."""
        logger.info("Upload queue worker running...")
        
        while self._is_running:
            try:
                # Wait for a task with timeout to allow checking _is_running
                try:
                    task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # None signals shutdown
                if task is None:
                    break
                
                # Process the task
                await self._process_task(task)
                self._queue.task_done()
                
            except Exception as e:
                logger.error(f"Queue worker error: {e}", exc_info=True)
        
        logger.info("Upload queue worker exiting")
    
    async def _process_task(self, task: UploadTask):
        """Process a single upload task."""
        from translations import get_text
        
        try:
            logger.info(f"[Photo #{task.photo_num}] Processing from queue...")
            
            # Download photo from Telegram
            logger.info(f"[Photo #{task.photo_num}] Downloading from Telegram: {task.photo_file_id}")
            file = await task.bot.get_file(task.photo_file_id)
            await file.download_to_drive(task.local_path)
            
            logger.info(f"[Photo #{task.photo_num}] Downloaded to: {task.local_path}")
            
            # Verify file exists after download
            if not os.path.exists(task.local_path):
                error_msg = f"File not found after download: {task.local_path}"
                logger.error(f"[Photo #{task.photo_num}] {error_msg}")
                if task.on_failure:
                    await task.on_failure(error_msg)
                return
            
            file_size = os.path.getsize(task.local_path)
            logger.info(f"[Photo #{task.photo_num}] File size: {file_size} bytes")
            
            # Upload to Google Drive (runs in thread pool)
            logger.info(f"[Photo #{task.photo_num}] Uploading to Drive: {task.drive_folder}")
            drive_service = get_drive_service()
            result = await asyncio.to_thread(
                drive_service.upload_file,
                task.local_path,
                task.drive_folder
            )
            
            if result.success:
                logger.info(f"[Photo #{task.photo_num}] ✅ Upload successful! File ID: {result.file_id}")
                if task.on_success:
                    await task.on_success()
            else:
                logger.warning(f"[Photo #{task.photo_num}] ❌ Upload failed: {result.error}")
                if task.on_failure:
                    await task.on_failure(result.error)
                else:
                    # Send default failure message
                    await task.bot.send_message(
                        chat_id=task.chat_id,
                        text=get_text(task.lang, 'photo_upload_failed')
                    )
                    
        except Exception as e:
            logger.error(f"[Photo #{task.photo_num}] ❌ Processing error: {type(e).__name__}: {e}", exc_info=True)
            try:
                if task.on_failure:
                    await task.on_failure(str(e))
                else:
                    await task.bot.send_message(
                        chat_id=task.chat_id,
                        text=get_text(task.lang, 'photo_upload_error')
                    )
            except Exception:
                pass  # Don't fail if notification fails
                
        finally:
            # Clean up temporary file
            if os.path.exists(task.local_path):
                os.remove(task.local_path)
                logger.info(f"[Photo #{task.photo_num}] Cleaned up temp file: {task.local_path}")


# Singleton accessor
def get_upload_queue() -> UploadQueue:
    """Get the singleton UploadQueue instance."""
    return UploadQueue()
