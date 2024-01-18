import math
import time

import obspython as obs


def script_description():
    return """Checks for Dota Shop showing or not, changes scene if it does."""


def switch_scene():
    """ gets list of scenes: it is the only way to get OBS "source" objects. OBS "scene" objects (which could be
    obtained without going through a list) cannot have their names retrieved using OBS functions, which make operations
    according to a scene name impossible.  """
    scenes_as_sources = obs.obs_frontend_get_scenes()
    current_scene_as_source = obs.obs_frontend_get_current_scene()
    current_scene_name = obs.obs_source_get_name(current_scene_as_source)
    for scene in scenes_as_sources:
        name = obs.obs_source_get_name(scene)
        if (current_scene_name == 'Scene A' and name == 'Scene B' or
                current_scene_name == 'Scene B' and name == 'Scene A'):
            obs.obs_frontend_set_current_scene(scene)
            break
    obs.source_list_release(scenes_as_sources)
    obs.obs_source_release(current_scene_as_source)


switch_scene()
