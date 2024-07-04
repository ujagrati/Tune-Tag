from .reader import BaseReader
import os
from pydub import AudioSegment
import numpy as np
from hashlib import sha1

class FileReader(BaseReader):
    def __init__(self, filename):
        super().__init__(filename)
        self.filename = filename

    def parse_audio(self):
        limit = None  # Adjust if you want to limit the duration
        # limit = 10

        songname, extension = os.path.splitext(os.path.basename(self.filename))

        try:
            audiofile = AudioSegment.from_file(self.filename)

            if limit:
                audiofile = audiofile[:limit * 1000]

            data = np.array(audiofile.get_array_of_samples(), dtype=np.int16)

            channels = []
            for chn in range(audiofile.channels):
                channels.append(data[chn::audiofile.channels])

            fs = audiofile.frame_rate

        except Exception as e:
            print(f"Error parsing audio: {e}")
            return None

        return {
            "songname": songname,
            "extension": extension,
            "channels": channels,
            "Fs": fs,
            "file_hash": self.parse_file_hash()
        }

    def parse_file_hash(self, blocksize=2**20):
        """ Generate a hash to uniquely identify a file. """
        s = sha1()

        with open(self.filename, "rb") as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    break
                s.update(buf)

        return s.hexdigest().upper()

