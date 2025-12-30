import ezdxf
from collections import Counter

def analyze_block_content(filename, block_name_filter):
    print(f"Analyzing {filename} for blocks containing '{block_name_filter}'...")
    try:
        doc = ezdxf.readfile(filename)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    found = False
    for block in doc.blocks:
        if block_name_filter in block.name:
            found = True
            print(f"\nBlock: {block.name}")
            layer_counts = Counter()
            types = Counter()
            for e in block:
                if hasattr(e.dxf, 'layer'):
                    layer_counts[e.dxf.layer] += 1
                types[e.dxftype()] += 1
            
            print("  Layers:", dict(layer_counts))
            print("  Types:", dict(types))

    if not found:
        print(f"No block found containing '{block_name_filter}'")

if __name__ == "__main__":
    analyze_block_content("osong-b1.dxf", "계단")
    analyze_block_content("osong-b1.dxf", "기둥")
