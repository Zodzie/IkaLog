#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  IkaLog
#  ======
#  Copyright (C) 2015 Takeshi HASEGAWA
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import gettext
import time
from ikalog import inputs
from ikalog.utils import *
from ikalog.plugin import IkaLogPlugin
import traceback

t = gettext.translation('IkaUI', 'locale', fallback=True)
_ = t.gettext


class Capture(IkaLogPlugin):

    """
    Constructor
    """

    def __init__(self):
        self.capture = None
        self._source_name = None

        self._initialize_input()

    def _register_input_plugin(self, cls):
        obj = cls()
        sources = obj.enumerate_sources()
        for i in range(len(sources)):
            name = sources[i]
            self.available_inputs.append({
                'index': i,
                'class': cls,
                'name': name
            })
        self._available_classes[cls.__name__] = cls

    def _initialize_input(self):
        self.available_inputs = []
        self._available_classes = {}

        # List all available input methods
        input_plugins = []
        if IkaUtils.isWindows():
            input_plugins.append(inputs.DirectShowCapture)
        if IkaUtils.isOSX():
            input_plugins.append(inputs.AVFoundationCapture)
        input_plugins.append(inputs.CVCapture)

        for plugin_class in input_plugins:
            try:
                self._register_input_plugin(plugin_class)
            except Exception:
                IkaUtils.dprint('Registration error: %s' %
                                plugin_class.__class__.__name__)
                IkaUtils.dprint(traceback.format_exc())

    """
    Device activation and deactivation
    """

    def _activate_input_nolock(self, cls, config):
        try:
            self._source_name = config['source_name']
            capture = cls()
            capture.select_source(self._source_name)
            self.capture = capture
            IkaUtils.dprint('%s: new input activated (%s, %s)' %
                            (self, cls, config))
            time.sleep(5)
        except:
            IkaUtils.dprint(
                '%s: new input cannot be activated (%s, %s)' % (self, cls, config))
            IkaUtils.dprint(traceback.format_exc())

            self.capture = None
            self._source_name = None
            return False
        return True

    def _activate_input(self, cls, config):
        # FIXME: lock
        self._activate_input_nolock(cls, config)

    def _deactivate_input_nolock(self):
        if self.is_active():
            IkaUtils.dprint('%s: Deactivating input...' % self)
            self.capture.stop()
            time.sleep(1)

        if self.capture is not None:
            IkaUtils.dprint('%s: Deinitializing input...' % self)
            del self.capture
            time.sleep(1)
        self.capture = None

    def _deactivate_input(self):
        # FIXME: lock
        self._deactivate_input_nolock()

    """
    IkaLog Plugins Interface
    """

    def on_initialize_plugin(self, context):
        engine = context['engine']['engine']

    def on_get_configuration(self):
        config = {}
        ro = {}

        for source in self.available_inputs:
            cls_name = source['class'].__name__
            name = source['name']

            # ro part
            if not (cls_name in ro):
                ro[cls_name] = []
            ro[cls_name].append({'source': name})

        if self.capture is not None:
            config['active_class'] = self.capture.__class__.__name__
        if self._source_name is not None:
            config['active_source_name'] = self._source_name

        config['read_only'] = ro
        return config

    def on_validate_configuration(self, config):
        if 'active_class' in config:
            try:
                cls = self._available_classes[config['active_class']]
            except KeyError:
                raise 'Not supported input'
        return True

    def on_set_configuration(self, config):
        self.on_validate_configuration(config)
        if 'active_class' in config:
            self._deactivate_input()
            time.sleep(1)
            cls = self._available_classes[config['active_class']]
            self._activate_input(cls, config[config['active_class']])

    """
    IkaLog Capture Interface
    """

    def read_frame(self):
        if self.capture is None:
            return None

        r = self.capture.read_frame()
        return r

    def is_active(self):
        if self.capture is None:
            return False
        return self.capture.is_active()

    def get_current_timestamp(self):
        if self.capture is None:
            return None
        return self.capture.get_current_timestamp()

    def get_epoch_time(self):
        if self.capture is None:
            return None
        return self.capture.get_epoch_time()

    def set_pos_msec(self, pos_msec):
        if self.capture is None:
            return
        return self.capture.set_pos_msec(pos_msec)

    def get_source_file(self):
        """
        Returns the source file if the input is from a file. Otherwise None.
        """
        if self.capture is None:
            return None
        return self.capture.get_source_file()

    def put_source_file(self, file_path):
        """
        Puts file_path to be processed and returns True,
        otherwise returns False if the instance does not support this method.
        """
        if self.capture is None:
            return False
        return self.capture.put_source_file(file_path)

    def on_eof(self):
        """
        Callback on EOFError. Returns True if a next data source is available.
        """
        if self.capture is None:
            return False
        return self.capture.on_eof()

    def start_recorded_file(self, file):
        IkaUtils.dprint(
            '%s: initalizing pre-recorded video file %s' % (self, file))
        self.realtime = False
        self.from_file = True
        self.capture.init_capture(file)
        self.fps = self.capture.cap.get(5)

    def enumerate_devices(self):
        if IkaUtils.isWindows():
            from ikalog.inputs.win.videoinput_wrapper import VideoInputWrapper
            cameras = VideoInputWrapper().get_device_list()

        else:
            cameras = [
                'IkaLog does not support camera enumeration on this platform.',
                'IkaLog does not support camera enumeration on this platform.',
                'IkaLog does not support camera enumeration on this platform.',
            ]

        if len(cameras) == 0:
            cameras = [_('No input devices found!')]
        return cameras

    def set_frame_rate(self, fps):
        pass

if __name__ == '__main__':
    obj = Capture()
    print(obj.available_inputs)
    import pprint
    pprint.pprint(obj.on_get_configuration())
    source = obj.on_get_configuration()['read_only'][
        'AVFoundationCapture'][0]['source']
    print(source)
    config = {'active_class': 'AVFoundationCapture',
              'AVFoundationCapture': {'source_name': source}}
    print(config)
    obj.set_configuration(config)
    pprint.pprint(obj.on_get_configuration())