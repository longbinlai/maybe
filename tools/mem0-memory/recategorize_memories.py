#!/usr/bin/env python3
"""
Recategorize memories from deprecated categories to active ones.
allocation_strategy → investment_style (for preferences and behavioral patterns)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mem0_memory.client import Mem0Client

def main():
    client = Mem0Client()
    
    # Memories to recategorize: allocation_strategy → investment_style
    recategorize_ids = [
        "09a69265",  # cash to cover 12 months of expenses
        "2aefe114",  # silent rules: intraday fluctuations below 1%
        "7ad13436",  # conservative risk preference with target allocation
        "9a663178",  # 5 alert trigger conditions
        "a199d511",  # Feishu push notifications have 4 levels
    ]
    
    print(f"Recategorizing {len(recategorize_ids)} memories...")
    print("allocation_strategy → investment_style")
    print()
    
    # Get full IDs by searching
    memories = client.get_all()
    full_id_map = {mem["id"][:8]: mem["id"] for mem in memories}
    
    updated = 0
    failed = 0
    
    for short_id in recategorize_ids:
        full_id = full_id_map.get(short_id)
        if not full_id:
            print(f"✗ Could not find memory {short_id}")
            failed += 1
            continue
        
        try:
            # Get current memory
            mem = next((m for m in memories if m["id"] == full_id), None)
            if not mem:
                print(f"✗ Could not retrieve memory {short_id}")
                failed += 1
                continue
            
            # Update category in metadata
            metadata = mem.get("metadata", {})
            old_category = metadata.get("category", "unknown")
            metadata["category"] = "investment_style"
            
            # Delete old and add new with updated category
            client.delete(full_id)
            client.add(
                content=mem.get("memory", ""),
                category="investment_style",
                metadata=metadata
            )
            
            print(f"✓ {short_id}: {old_category} → investment_style")
            updated += 1
            
        except Exception as e:
            print(f"✗ Failed to recategorize {short_id}: {e}")
            failed += 1
    
    print()
    print(f"Recategorization complete: {updated} updated, {failed} failed")
    print()
    
    # Show final state
    print("Final Mem0 state (pure subjective wisdom):")
    memories = client.get_all()
    print(f"Total: {len(memories)} memories")
    print()
    
    # Group by category
    by_category = {}
    for mem in memories:
        category = mem.get("metadata", {}).get("category", "unknown")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(mem)
    
    for category, mems in sorted(by_category.items()):
        print(f"[{category}] ({len(mems)} memories)")
        for mem in mems:
            content = mem.get("memory", "")[:80]
            print(f"  • {content}...")
        print()

if __name__ == "__main__":
    main()
