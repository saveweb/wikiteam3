import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Estimate size of images')
    parser.add_argument('images_list', help='Path to images.txt')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    arg = parse_args()
    images_list = arg.images_list
    size = 0
    with open(images_list, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                size += int(line.strip().split('\t')[3])
            except Exception:
                pass
    print(size // 1024 // 1024 // 1024, 'GB')