import tempfile
import unittest
import unittest.mock
import wave
from pathlib import Path
from ai02_groq_stt_acceptance import wer, words, segments_ok, inspect, run

class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.file=Path(self.temp.name)/"voice.wav"
        with wave.open(str(self.file),"wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000)
            f.writeframes(b"\x00\x00"*16000*5)
        self.reference="A literatura brasileira possui uma longa historia."
        self.response={"text":self.reference,"segments":[{"start":.1,"end":4.8,"text":self.reference}]}
    def tearDown(self):
        self.temp.cleanup()
    def test_wer(self):
        self.assertEqual(wer("LITERATURA brasileira","literatura, BRASILEIRA!"),0)
        self.assertAlmostEqual(wer("um dois tres","um tres"),1/3,places=5)
    def test_timestamps(self):
        self.assertTrue(segments_ok(self.response["segments"],5))
        self.assertFalse(segments_ok([{"start":-1,"end":1,"text":"errado"}],5))
        self.assertFalse(segments_ok([],5))
    def test_evaluate(self):
        data=self.file.read_bytes()
        self.assertEqual(inspect(data,5,self.reference,self.response)["result"],"PASS_FIXTURE_ONLY")
        self.assertEqual(inspect(data,5,self.reference,{**self.response,"text":"fala inventada"})["result"],"FAIL_QUALITY")
    def test_no_network_default(self):
        with unittest.mock.patch("ai02_groq_stt_acceptance.request_once") as net:
            self.assertEqual(run(self.file,self.reference)["result"],"NO_LIVE_CALL")
            with unittest.mock.patch.dict("os.environ",{"GROQ_API_KEY":""}):
                self.assertEqual(run(self.file,self.reference,live=True)["result"],"BLOCKED_NO_AUTHORIZED_KEY")
            net.assert_not_called()


    def test_user_agent_request(self):
        import io
        from ai02_groq_stt_acceptance import request_once
        def fake_open(req, timeout):
            self.assertEqual(req.get_header("User-agent"), "anthares-ai02-acceptance/1.0")
            self.assertEqual(req.get_method(), "POST")
            r=io.BytesIO(b'{"text":"ok","segments":[]}')
            r.headers={}
            return r
        with unittest.mock.patch("ai02_groq_stt_acceptance.urllib.request.urlopen", side_effect=fake_open):
            payload, headers, latency = request_once(b"synthetic audio", "TEST_ONLY_NO_NETWORK")
            self.assertEqual(payload["text"], "ok")

