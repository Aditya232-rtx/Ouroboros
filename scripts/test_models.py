"""
Test script for verifying model loading with temporary models.
Tests all 3 temporary models to ensure they load correctly.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import get_model
from config.model_configs import MODEL_REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_model_loading():
    """Test loading all temporary models"""
    
    logger.info("="*60)
    logger.info("Testing Temporary Model Loading")
    logger.info("="*60)
    
    results = {}
    
    for agent_name, config in MODEL_REGISTRY.items():
        logger.info(f"\n🔄 Testing {agent_name.upper()} Agent Model...")
        logger.info(f"   Model: {config.name}")
        logger.info(f"   Path: {config.model_path}")
        logger.info(f"   VRAM: ~{config.n_gpu_layers * 0.1:.1f} GB (approx)")
        
        try:
            model = get_model(agent_name)
            
            if model:
                logger.info(f"   ✅ {agent_name.upper()} model loaded successfully!")
                
                # Test simple inference
                test_prompt = "Hello, test"
                response = model.create_completion(
                    prompt=test_prompt,
                    max_tokens=10,
                    temperature=0.1
                )
                
                logger.info(f"   ✅ Inference test passed")
                results[agent_name] = "SUCCESS"
            else:
                logger.error(f"   ❌ {agent_name.upper()} model returned None")
                results[agent_name] = "FAILED - returned None"
                
        except Exception as e:
            logger.error(f"   ❌ {agent_name.upper()} failed: {e}")
            results[agent_name] = f"FAILED - {str(e)}"
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Test Summary")
    logger.info("="*60)
    
    for agent, result in results.items():
        status = "✅" if result == "SUCCESS" else "❌"
        logger.info(f"{status} {agent.upper()}: {result}")
    
    success_count = sum(1 for r in results.values() if r == "SUCCESS")
    total_count = len(results)
    
    logger.info(f"\nTotal: {success_count}/{total_count} models loaded successfully")
    
    if success_count == total_count:
        logger.info("\n🎉 All models loaded successfully!")
        return 0
    else:
        logger.error("\n⚠️ Some models failed to load")
        return 1


if __name__ == "__main__":
    exit_code = test_model_loading()
    sys.exit(exit_code)
