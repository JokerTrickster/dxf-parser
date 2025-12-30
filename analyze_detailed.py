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
    print("\n=== All Layers ===")
    layers = sorted([layer.dxf.name for layer in doc.layers])
    for layer in layers:
        print(f"  {layer}")

    # List all block names
    print("\n=== All Blocks ===")
    block_names = sorted([block.name for block in doc.blocks])
    for name in block_names:
        print(f"  {name}")

    # Check for layer usage in blocks
    print("\n=== Layer Usage in Blocks ===")
    layer_usage = Counter()
    for block in doc.blocks:
        for e in block:
            if hasattr(e.dxf, 'layer'):
                layer_usage[e.dxf.layer] += 1
    
    for layer, count in layer_usage.most_common(20):
        print(f"  {layer}: {count}")

if __name__ == "__main__":
    analyze_dxf("osong-b1.dxf")
