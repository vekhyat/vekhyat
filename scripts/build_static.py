"""Export readable, nonanimated fallbacks for every delivered SVG."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)

def main():
    count=0
    for folder in (ROOT/'assets',ROOT/'dist'):
        target=folder/'static';target.mkdir(exist_ok=True)
        for source in sorted(folder.glob('*.svg')):
            tree=ET.parse(source);root=tree.getroot()
            for child in list(root):
                if child.tag==f'{{{NS}}}style': root.remove(child)
            tree.write(target/source.name,encoding='utf-8',xml_declaration=False)
            count+=1
    print(f'Built {count} static SVG fallbacks')

if __name__=='__main__': main()
