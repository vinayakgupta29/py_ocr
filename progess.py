import sys
import time

def loading_bar(total=50, duration=2):
    for i in range(total + 1):
        percent = int((i / total) * 100)
        bar = '#' * i + '-' * (total - i)
        sys.stdout.write(f'\r[{bar}] {percent:3d}%')
        sys.stdout.flush()
        time.sleep(duration / total)
    print("\nDone!")

# Example usage
if __name__ == "__main__":
    loading_bar()

