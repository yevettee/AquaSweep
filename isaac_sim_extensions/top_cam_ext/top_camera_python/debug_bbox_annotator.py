"""
Debug script to check if Replicator bbox annotator is working.

Run in Isaac Sim Script Editor:
exec(open("/home/woody/AquaSweep/isaac_sim_extensions/top_cam_ext/top_camera_python/debug_bbox_annotator.py").read())
"""

import omni.usd
import omni.replicator.core as rep
from pxr import Sdf, UsdGeom, Usd

RESOLUTION = (1280, 720)
POOL_ID = 2  # Test with Pool_2 (has fish)


async def debug_annotator():
    print("\n" + "="*60)
    print("  DEBUG: Replicator BBox Annotator (v4 - rep.get.prims)")
    print("="*60)
    
    stage = omni.usd.get_context().get_stage()
    if not stage:
        print("ERROR: No stage!")
        return
    
    # Step 1: Find fish prims
    print("\n[1] Finding fish prims...")
    fish_paths = []
    pool_path = f"/World/Pools/Pool_{POOL_ID}"
    pool_prim = stage.GetPrimAtPath(pool_path)
    
    if not pool_prim.IsValid():
        print(f"  ERROR: {pool_path} not found!")
        return
    
    for child in pool_prim.GetChildren():
        name = child.GetName()
        if name.startswith("Sturgeon_"):
            fish_paths.append(str(child.GetPath()))
            print(f"  Found: {child.GetPath()}")
    
    if not fish_paths:
        print("  No fish found!")
        return
    
    # Step 2: Apply semantic labels using rep.get.prims + rep.modify.semantics
    print("\n[2] Applying semantic labels using Replicator API...")
    
    try:
        # Method 1: Use rep.get.prims with path_pattern
        fish_group = rep.get.prims(path_pattern=f"/World/Pools/Pool_{POOL_ID}/Sturgeon_.*")
        with fish_group:
            rep.modify.semantics([("class", "sturgeon")])
        print("  Method 1 (path_pattern): OK")
    except Exception as e:
        print(f"  Method 1 failed: {e}")
    
    try:
        # Method 2: Use rep.get.prims with semantics filter (to check existing)
        # This should find prims that already have semantics
        existing = rep.get.prims(semantics=[("class", "sturgeon")])
        print(f"  Prims with 'sturgeon' semantic: checking...")
    except Exception as e:
        print(f"  Method 2 check failed: {e}")
    
    try:
        # Method 3: Apply to each path individually
        for fish_path in fish_paths:
            prim_group = rep.get.prims(path_pattern=fish_path)
            with prim_group:
                rep.modify.semantics([("class", "sturgeon")])
        print(f"  Method 3 (individual paths): OK for {len(fish_paths)} prims")
    except Exception as e:
        print(f"  Method 3 failed: {e}")
    
    # Step 3: Verify by checking USD attributes
    print("\n[3] Verifying USD attributes...")
    test_prim = stage.GetPrimAtPath(fish_paths[0])
    print(f"  Checking: {fish_paths[0]}")
    for attr in test_prim.GetAttributes():
        name = attr.GetName()
        if "semantic" in name.lower() or "Semantic" in name:
            print(f"    {name} = {attr.Get()}")
    
    # Step 4: Create render product
    print("\n[4] Creating render product...")
    cam_path = f"/World/Pools/Pool_{POOL_ID}/TopCamera"
    rp = rep.create.render_product(cam_path, RESOLUTION)
    print("  OK")
    
    # Step 5: Annotators
    print("\n[5] Creating annotators...")
    
    # Try different semantic types
    bbox_class = rep.AnnotatorRegistry.get_annotator(
        "bounding_box_2d_tight",
        init_params={"semanticTypes": ["class"]}
    )
    bbox_class.attach([rp])
    
    # Also instance ID based
    instance_id = rep.AnnotatorRegistry.get_annotator("instance_id_segmentation")
    instance_id.attach([rp])
    
    sem_seg = rep.AnnotatorRegistry.get_annotator(
        "semantic_segmentation",
        init_params={"semanticTypes": ["class"]}
    )
    sem_seg.attach([rp])
    
    print("  Annotators attached")
    
    # Step 6: Run orchestrator to update render
    print("\n[6] Stepping orchestrator...")
    
    # Run multiple steps
    for i in range(5):
        await rep.orchestrator.step_async()
    print("  5 steps completed")
    
    # Step 7: Results
    print("\n[7] Results:")
    
    bbox_data = bbox_class.get_data()
    print(f"\n  bounding_box_2d_tight:")
    if bbox_data:
        print(f"    Boxes: {len(bbox_data.get('data', []))}")
        print(f"    idToLabels: {bbox_data.get('info', {}).get('idToLabels', {})}")
    
    sem_data = sem_seg.get_data()
    print(f"\n  semantic_segmentation:")
    if sem_data:
        labels = sem_data.get("info", {}).get("idToLabels", {})
        print(f"    idToLabels: {labels}")
        # Check if sturgeon is in labels
        for k, v in labels.items():
            if "sturgeon" in str(v).lower():
                print(f"    FOUND 'sturgeon' label!")
    
    inst_data = instance_id.get_data()
    print(f"\n  instance_id_segmentation:")
    if inst_data:
        info = inst_data.get("info", {})
        print(f"    Keys: {info.keys() if isinstance(info, dict) else 'N/A'}")
    
    # Cleanup
    bbox_class.detach()
    instance_id.detach()
    sem_seg.detach()
    
    print("\n" + "="*60)
    print("  DEBUG COMPLETE")
    print("="*60)
    print("\n  Next step: Try manual semantic labeling in Isaac Sim UI")
    print("  Then re-run to confirm the correct schema.")
    print("="*60 + "\n")


# Run
import asyncio
asyncio.ensure_future(debug_annotator())
