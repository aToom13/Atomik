import asyncio
import os
import pyaudio
import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000 # 16kHz is standard for speech models
CHUNK_SIZE = 512

class AudioHandler:
    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.setup_echo_cancellation()
        self.input_stream = None
        self.output_stream = None

    def setup_echo_cancellation(self):
        """Loads the echo-cancel module and sets it as default."""
        try:
            # Check if module is loaded
            check_cmd = "pactl list modules short | grep module-echo-cancel"
            result = subprocess.run(check_cmd, shell=True, stdout=subprocess.PIPE)
            if not result.stdout:
                print("Loading PulseAudio Echo Cancellation module...")
                subprocess.run("pactl load-module module-echo-cancel", shell=True, check=True)
            else:
                print("PulseAudio Echo Cancellation module already loaded.")
            
            # Set defaults
            print("Setting Echo Cancellation as default source/sink...")
            subprocess.run("pactl set-default-source echo-cancel-source", shell=True)
            subprocess.run("pactl set-default-sink echo-cancel-sink", shell=True)
            
        except Exception as e:
            print(f"Warning: Could not setup Echo Cancellation: {e}")

    def start_input_stream(self):
        """Starts the microphone input stream with robust device selection."""
        # Try default first
        try:
            self.input_stream = self.pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            print("Microphone initialized successfully (Default Device).")
            return
        except Exception as e:
            print(f"Default device failed at {RATE}Hz: {e}")
            print("Searching for compatible input device...")

        # Search for working device
        available_device_index = None
        for i in range(self.pya.get_device_count()):
            try:
                info = self.pya.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    # Test open
                    stream = self.pya.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=CHUNK_SIZE
                    )
                    stream.close()
                    available_device_index = i
                    print(f"Found compatible device: [{i}] {info['name']}")
                    # Prefer PulseAudio if found
                    if "pulse" in info['name'].lower():
                        break
            except Exception:
                continue

        if available_device_index is not None:
             try:
                self.input_stream = self.pya.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=available_device_index,
                    frames_per_buffer=CHUNK_SIZE
                )
                print(f"Microphone initialized using device index {available_device_index}.")
             except Exception as e:
                 print(f"Error initializing microphone on index {available_device_index}: {e}")
                 sys.exit(1)
        else:
            print("No compatible 16kHz input device found.")
            sys.exit(1)

    def start_output_stream(self):
        """Starts the speaker output stream with robust device selection."""
        output_rate = 24000  # Gemini outputs at 24kHz
        
        # Try default first
        try:
            self.output_stream = self.pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=output_rate,
                output=True
            )
            self.output_rate = output_rate
            print(f"Speaker initialized successfully (Default Device at {output_rate}Hz).")
            return
        except Exception as e:
            print(f"Default speaker failed at {output_rate}Hz: {e}")
            print("Searching for compatible output device...")

        # Search for working device
        available_device_index = None
        for i in range(self.pya.get_device_count()):
            try:
                info = self.pya.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    # Test open at 24kHz
                    stream = self.pya.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=output_rate,
                        output=True,
                        output_device_index=i
                    )
                    stream.close()
                    available_device_index = i
                    print(f"Found compatible output device: [{i}] {info['name']}")
                    # Prefer PulseAudio if found
                    if "pulse" in info['name'].lower():
                        break
            except Exception:
                continue

        if available_device_index is not None:
            try:
                self.output_stream = self.pya.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=output_rate,
                    output=True,
                    output_device_index=available_device_index
                )
                self.output_rate = output_rate
                print(f"Speaker initialized using device index {available_device_index} at {output_rate}Hz.")
            except Exception as e:
                print(f"Error initializing speaker on index {available_device_index}: {e}")
                sys.exit(1)
        else:
            print("No compatible 24kHz output device found.")
            sys.exit(1)

    def read_chunk(self):
        if self.input_stream:
            try:
                # disable exception_on_overflow for smoother reading
                return self.input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
            except Exception as e:
                print(f"Error reading audio: {e}")
                return None
        return None

    def write_chunk(self, data):
        if self.output_stream:
            try:
                self.output_stream.write(data)
            except Exception as e:
                print(f"Error writing audio: {e}")

    def cleanup(self):
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.pya.terminate()
