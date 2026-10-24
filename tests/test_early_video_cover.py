import asyncio,unittest
from utils.early_video_cover import prepare_video_and_cover
class EarlyCoverGateTests(unittest.IsolatedAsyncioTestCase):
 async def test_early_cover_and_barrier(self):
  events=[];finished=asyncio.Event()
  async def video():await finished.wait();events.append('video')
  async def ready():return True
  async def cover():events.append('cover');finished.set()
  await prepare_video_and_cover(video,ready,cover,poll_interval=.001)
  self.assertEqual(events,['cover','video'])
 async def test_no_early_entry_falls_back_after_video(self):
  events=[]
  async def video():events.append('video')
  async def ready():return False
  async def cover():events.append('cover')
  await prepare_video_and_cover(video,ready,cover,poll_interval=.001)
  self.assertEqual(events,['video','cover'])
 async def test_cover_failure_cancels_waiter(self):
  stopped=asyncio.Event()
  async def video():
   try:await asyncio.sleep(10)
   finally:stopped.set()
  async def ready():await asyncio.sleep(0);return True
  async def cover():raise RuntimeError('cover failed')
  with self.assertRaisesRegex(RuntimeError,'cover failed'):await prepare_video_and_cover(video,ready,cover)
  self.assertTrue(stopped.is_set())
 async def test_failed_video_never_runs_late_cover(self):
  async def video():return False
  async def ready():return False
  async def cover():self.fail('must not set cover after upload failure')
  with self.assertRaisesRegex(RuntimeError,'视频上传失败'):await prepare_video_and_cover(video,ready,cover,poll_interval=.001)
 async def test_video_done_during_cover_does_not_release_barrier(self):
  events=[];started=asyncio.Event()
  async def video():await started.wait();events.append('video')
  async def ready():return True
  async def cover():started.set();await asyncio.sleep(.02);events.append('cover')
  await prepare_video_and_cover(video,ready,cover);events.append('return')
  self.assertEqual(events,['video','cover','return'])

 async def test_platform_not_ready_defers_cover_until_video_complete(self):
  from utils.early_video_cover import CoverNotReady
  done=asyncio.Event();events=[]
  async def video():await done.wait();events.append('video')
  async def ready():return True
  async def cover():
   if not done.is_set():
    events.append('deferred');asyncio.get_running_loop().call_later(.02,done.set)
    raise CoverNotReady('still uploading')
   events.append('cover')
  await prepare_video_and_cover(video,ready,cover,poll_interval=.001)
  self.assertEqual(events,['deferred','video','cover'])
