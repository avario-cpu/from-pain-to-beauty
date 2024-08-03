import asyncio

# Event to signal that secondary windows have been spawned and are ready to be managed
secondary_windows_spawned = asyncio.Event()
# Event to signal that we should mute SSIM prints to the console
mute_ssim_prints = asyncio.Event()
