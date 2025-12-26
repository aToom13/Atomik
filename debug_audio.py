import pyaudio

p = pyaudio.PyAudio()

print("Available Audio Devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"Index {i}: {info['name']}")
    print(f"  Max Input Channels: {info['maxInputChannels']}")
    print(f"  Default Sample Rate: {info['defaultSampleRate']}")
    
    # Test 16000Hz support
    try:
        if info['maxInputChannels'] > 0:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, input_device_index=i)
            print("  [PASS] Supports 16000Hz Input")
            stream.close()
        else:
             print("  [SKIP] Output only device")
             
    except Exception as e:
        print(f"  [FAIL] 16000Hz Input: {e}")

p.terminate()
