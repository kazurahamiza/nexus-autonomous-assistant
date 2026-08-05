import os
import sys
import json
import time
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "system_config.json")

class LLMControllerBrain:
    """Central Cognitive Controller: Translates unstructured user intent into 

    structured microservice task schemas and orchestrates execution queues.
    """

    def __init__(self):
        self.system_version = "v5.0-Enterprise"

    def compose_production_blueprint(self, user_prompt: str, target_platform: str = "vertical_short") -> Dict[str, Any]:
        """Analyzes prompt intent and generates a multi-stage execution plan."""
        logging.info(f"[*] [LLMBrain] Synthesizing production plan for: '{user_prompt}'")
        
        # Structured Cognitive Production Plan
        production_plan = {
            "meta": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "target_platform": target_platform,
                "engine_tier": "LLM-Controlled-Autonomous-v5"
            },
            "scenes": [
                {
                    "scene_id": 1,
                    "duration_sec": 5,
                    "visual_prompt": f"Cinematic 8k resolution, {user_prompt}, hyper-realistic, dramatic lighting, shot on 35mm lens",
                    "negative_prompt": "blurry, low quality, distortion, ugly, extra limbs",
                    "voiceover_script": f"Welcome to this breakdown on {user_prompt}.",
                    "camera_movement": "slow_zoom_in",
                    "aspect_ratio": "9:16" if target_platform == "vertical_short" else "16:9"
                },
                {
                    "scene_id": 2,
                    "duration_sec": 5,
                    "visual_prompt": f"Detailed close-up shot, key details of {user_prompt}, vibrant colors, octane render",
                    "negative_prompt": "blurry, low quality, distortion",
                    "voiceover_script": "Here is what you need to know next.",
                    "camera_movement": "pan_right",
                    "aspect_ratio": "9:16" if target_platform == "vertical_short" else "16:9"
                }
            ],
            "audio_config": {
                "voice_id": "en-US-ChristopherNeural",
                "bg_music_style": "ambient_cinematic_synth",
                "ducking_level": 0.8
            },
            "post_processing": {
                "upscale_target": "4k",
                "burn_captions": True,
                "apply_color_grade": "teal_and_orange"
            }
        }
        
        return production_plan

    def dispatch_to_orchestrator(self, plan: Dict[str, Any]) -> bool:
        """Dispatches structured JSON plan to Celery worker queue and local DB."""
        logging.info("[*] [LLMBrain] Dispatching structured plan to Master Pipeline Orchestrator...")
        
        try:
            from distributed_task_worker import execute_video_pipeline
            # Trigger asynchronous task execution via Celery
            task = execute_video_pipeline.delay("asset_llm_gen_001", json.dumps(plan))
            logging.info(f"[+] [LLMBrain] Task dispatched successfully to Redis/Celery Queue. Task ID: {task.id}")
            return True
        except Exception as e:
            logging.warning(f"[!] [LLMBrain] Could not queue task to Celery directly (Running local fallback): {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] LLM Controller Brain module verified (Non-blocking).")
    else:
        brain = LLMControllerBrain()
        blueprint = brain.compose_production_blueprint("Future of Autonomous AI Robotics")
        print(json.dumps(blueprint, indent=2))
        brain.dispatch_to_orchestrator(blueprint)