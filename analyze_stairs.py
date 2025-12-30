import ezdxf
from collections import Counter

def analyze_dxf(filename):
    print(f"Analyzing {filename}...")
    try:
        doc = ezdxf.readfile(filename)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # List all layers
    print("\n=== Layers ===")
    layers = [layer.dxf.name for layer in doc.layers]
    print(f"Total layers: {len(layers)}")
    for layer in sorted(layers):
        if 'STAIR' in layer.upper() or '계단' in layer:
            print(f"  [POTENTIAL STAIR LAYER] {layer}")

    # List all block names
    print("\n=== Blocks ===")
    block_names = [block.name for block in doc.blocks]
    print(f"Total blocks: {len(block_names)}")
    stair_blocks = []
    for name in block_names:
        if 'STAIR' in name.upper() or '계단' in name:
            stair_blocks.append(name)
    
    print(f"Found {len(stair_blocks)} potential stair blocks:")
    for name in sorted(stair_blocks):
        print(f"  {name}")

    # Analyze entities in 'PLAN' layer if it exists
    print("\n=== PLAN Layer Analysis ===")
    plan_entities = Counter()
    
    # Check Modelspace
    msp = doc.modelspace()
    for e in msp:
        if e.dxf.layer == 'PLAN':
            plan_entities[e.dxftype()] += 1
            
    # Check Blocks (as `dxf_parking_with_building.py` looks inside blocks)
    block_plan_entities = Counter()
    for block in doc.blocks:
        for e in block:
            if e.dxf.layer == 'PLAN':
                block_plan_entities[e.dxftype()] += 1

    print("Modelspace PLAN entities:", dict(plan_entities))
    print("Block content PLAN entities:", dict(block_plan_entities))

if __name__ == "__main__":
    analyze_dxf("osong-b1-2.dxf")
