# memora/setup/infrastructure.py

import frappe
import redis
import os
import json

def run_auto_configuration():
    """
    Main entry point to configure infrastructure automatically.
    This should run on 'after_migrate'.
    """
    configure_redis_safety()
    optimize_worker_config()
    verify_table_structure()

def configure_redis_safety():
    """
    Risk 1: Redis Memory Bomb
    Solution: Force Redis to evict old keys if memory is full.
    """
    try:
        # Get Redis credentials from site config
        conf = frappe.get_site_config()
        redis_url = conf.get('redis_cache') or "redis://localhost:13000"
        
        # Connect to Redis
        r = redis.from_url(redis_url)
        
        # 1. Set Eviction Policy to 'allkeys-lru' (Delete oldest keys when full)
        # This prevents the server from crashing when RAM is full
        r.config_set('maxmemory-policy', 'allkeys-lru')
        
        # 2. Set Max Memory (Optional - usually better set in redis.conf, 
        # but we can set a safety limit here if not set, e.g., 2GB)
        # current_max = r.config_get('maxmemory').get('maxmemory')
        # if current_max == '0': # 0 means unlimited (dangerous)
        #     r.config_set('maxmemory', '2gb') 
        
        frappe.logger().info("✅ Redis Auto-Config: Set policy to allkeys-lru")
        
    except Exception as e:
        frappe.logger().warning(f"⚠️ Redis Auto-Config Failed: {e}")

def verify_table_structure():
    """
    Risk 2: Restore Nightmare
    Solution: Check if partitioning exists, if not, re-run the patch.
    """
    try:
        # Check if table is actually partitioned
        is_partitioned = frappe.db.sql("""
            SELECT count(*) FROM information_schema.partitions 
            WHERE table_name = 'tabPlayer Memory Tracker' 
            AND partition_name IS NOT NULL
        """)[0][0] > 1

        if not is_partitioned:
            frappe.logger().warning("⚠️ Table not partitioned! Re-applying patch...")
            # Re-run the patch logic manually
            from memora.patches.v1_0.setup_partitioning import execute
            execute()
            frappe.logger().info("✅ Partitioning Re-applied successfully.")
            
    except Exception as e:
        frappe.logger().error(f"Partition Check Failed: {e}")

def optimize_worker_config():
    """
    Risk 3: Queue Jam
    Solution: Update common_site_config.json to ensure multiple workers.
    Note: Requires 'bench setup supervisor' & restart to take effect fully.
    """
    try:
        config_path = "sites/common_site_config.json"
        if not os.path.exists(config_path):
            return

        with open(config_path, 'r') as f:
            config = json.load(f)

        changed = False
        
        # Ensure we have enough workers for our queue
        # Frappe standard config for workers
        workers = config.get('workers', {})
        if not workers.get('srs_write'):
            workers['srs_write'] = 2 # Default to 2 workers
            config['workers'] = workers
            changed = True
            
        if changed:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            frappe.logger().info("✅ Worker Config Updated: Set srs_write workers to 2")
            # Note: User still needs to run 'bench setup supervisor' to apply this to OS
            
    except Exception as e:
        frappe.logger().warning(f"Worker Auto-Config Failed: {e}")