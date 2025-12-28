from tools.web.youtube import get_youtube_content
from tools.executor import execute_tool
import json

def test_youtube_direct():
    print("Testing direct tool access...")
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo (Short video)
    data = get_youtube_content(url)
    
    if "error" in data:
        print(f"FAILED: {data['error']}")
    else:
        print(f"SUCCESS: {data['metadata']['title']}")
        print(f"Transcript length: {len(data['full_transcript'])}")

def test_executor():
    print("\nTesting via executor...")
    result = execute_tool("analyze_youtube", {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "query": "Who is in the video?"
    })
    print(f"Executor Result (Preview):\n{result[:500]}...")

if __name__ == "__main__":
    test_youtube_direct()
    test_executor()
