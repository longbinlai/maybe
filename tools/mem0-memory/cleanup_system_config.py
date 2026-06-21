#!/usr/bin/env python3
"""
Clean up system configuration memories from Mem0.
These belong in config files, not in subjective wisdom memory.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mem0_memory.client import Mem0Client

def main():
    client = Mem0Client()
    
    # System configuration memories (should be in config files, not Mem0)
    system_config_ids = [
        "05e7cae4-506f-48ce-b595-6a8ae61993fc",  # AI infrastructure uses 百炼
        "509c409a-7b6e-4d84-a18b-b114e0ca66cc",  # DataHub manages 20 macro sources
        "6c84bdd8-1bd6-4030-9167-031ff04a6b23",  # System uses Maybe Finance (Rails)
        "6cbe0aae-f350-4170-aa0f-6ac7c8d0bcba",  # User began using Mem0 on June 20
        "ab36363d-d24c-4e3a-84d0-6dc63f860491",  # System health check runs every 5 min
        "f1e4a616-9254-47f7-9038-b7fbea8ffb57",  # System has 7 scheduled tasks
    ]
    
    print(f"Cleaning up {len(system_config_ids)} system configuration memories...")
    print("(These belong in config files, not Mem0)")
    print()
    
    deleted = 0
    failed = 0
    
    for memory_id in system_config_ids:
        try:
            client.delete(memory_id)
            print(f"✓ Deleted {memory_id}")
            deleted += 1
        except Exception as e:
            print(f"✗ Failed to delete {memory_id}: {e}")
            failed += 1
    
    print()
    print(f"Cleanup complete: {deleted} deleted, {failed} failed")
    print()
    
    # Show remaining memories
    print("Remaining memories (should be pure subjective wisdom):")
    memories = client.get_all()
    print(f"Total: {len(memories)} memories")
    print()
    for mem in memories:
        memory_id = mem.get("id", "unknown")
        category = mem.get("metadata", {}).get("category", "unknown")
        content = mem.get("memory", "")[:100]
        print(f"  [{memory_id[:8]}] [{category}]")
        print(f"    {content}...")
        print()

if __name__ == "__main__":
    main()
