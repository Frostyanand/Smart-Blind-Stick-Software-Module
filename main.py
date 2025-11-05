# main.py
import time
import threading
import queue
import pyttsx3
import config

# internal
_tts_queue = queue.Queue()
_worker_thread = None
_worker_alive = threading.Event()


def _tts_worker():
    """
    Worker thread: initializes engine and sequentially processes queue items.
    Each queue item is a tuple (text, repeat, gap).
    
    NOTE: Due to pyttsx3 issues on Windows, we reinitialize engine for each speech.
    """
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    print("[TTS] Worker thread starting...")
    
    _worker_alive.set()
    while _worker_alive.is_set():
        try:
            item = _tts_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if item is None:
            break  # shutdown sentinel

        text, repeat, gap = item
        success = False
        engine = None
        
        try:
            for i in range(repeat):
                print(f"[TTS] Speaking now: {text} ({i+1}/{repeat})")
                start_time = time.time()
                
                # Reinitialize engine for each speech (fixes Windows pyttsx3 bug)
                try:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', config.TTS_RATE)
                    engine.setProperty('volume', config.TTS_VOLUME)
                except Exception as init_error:
                    print(f"[TTS] Engine init failed: {init_error}")
                    raise
                
                # Queue the text and speak
                engine.say(text)
                engine.runAndWait()
                
                elapsed = time.time() - start_time
                
                # Clean up engine after each speech
                try:
                    engine.stop()
                    del engine
                    engine = None
                except:
                    pass
                
                print(f"[TTS] Completed in {elapsed:.2f}s")
                
                if i < repeat - 1:  # don't sleep after last repeat
                    time.sleep(gap)
            
            success = True
            consecutive_errors = 0  # reset error counter on success
            
        except Exception as e:
            print(f"[TTS] ERROR while speaking '{text}': {e}")
            consecutive_errors += 1
            
            # Clean up engine on error
            try:
                if engine:
                    engine.stop()
                    del engine
            except:
                pass
                    
        finally:
            _tts_queue.task_done()

    # cleanup
    print("[TTS] Worker shutting down...")
    _worker_alive.clear()


def start_tts_worker():
    """Start the TTS worker thread (idempotent)."""
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_tts_worker, daemon=True)
        _worker_thread.start()
        # give worker a moment
        timeout = 2.0
        t0 = time.time()
        while not _worker_alive.is_set() and time.time() - t0 < timeout:
            time.sleep(0.05)
        
        if not _worker_alive.is_set():
            print("[TTS] WARNING: TTS worker did not start within timeout")
        else:
            print("[TTS] Worker thread started successfully")
            print("[TTS] NOTE: Engine will be reinitialized for each speech (Windows fix)")


def stop_tts_worker():
    """Stop the TTS worker cleanly."""
    _worker_alive.clear()
    # send sentinel
    try:
        _tts_queue.put_nowait(None)
    except Exception:
        pass


def enqueue_speak(text, repeat=None, gap=None):
    """Add a speak job to the TTS queue. Cooldown is handled by model.py."""
    if repeat is None:
        repeat = config.TTS_REPEAT
    if gap is None:
        gap = 0.3
    
    if not _worker_alive.is_set():
        print("[TTS] Worker not alive, attempting to restart...")
        start_tts_worker()
        time.sleep(0.5)
        if not _worker_alive.is_set():
            print("[TTS] Failed to restart worker, skipping speech")
            return
    
    # Monitor queue size to detect backlog
    qsize = _tts_queue.qsize()
    if qsize > 5:
        print(f"[TTS] WARNING: Queue backlog ({qsize} items), skipping '{text}'")
        return
    
    print(f"[TTS] Enqueuing: {text} (repeat={repeat}, queue_size={qsize})")
    _tts_queue.put((text, repeat, gap))



# If run directly, quick manual test
if __name__ == "__main__":
    start_tts_worker()
    print("Running quick test: will say 'test' three times.")
    enqueue_speak("test", repeat=3, gap=1.0)
    # give it some time
    time.sleep(5)
    stop_tts_worker()
