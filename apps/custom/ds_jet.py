#!/usr/bin/env python3
import sys
sys.path.append('../')
from optparse import OptionParser
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
import pyds

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3

def main(args):
    parser = OptionParser()
    parser.add_option("--width" , dest="width", help="Width", metavar="STR")
    parser.add_option("--height", dest="height", help="Height", metavar="STR")
 
    (options, args) = parser.parse_args()
    width = int(options.width)
    height = int(options.height)
    device = args[0]

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # create pipeline
    pipeline = Gst.Pipeline()
    source = Gst.ElementFactory.make("v4l2src", "usb-cam-source")
    caps_v4l2src = Gst.ElementFactory.make("capsfilter", "v4l2src_caps")
    vidconvsrc = Gst.ElementFactory.make("videoconvert", "convertor_src1")
    nvvidconvsrc = Gst.ElementFactory.make("nvvideoconvert", "convertor_src2")
    caps_vidconvsrc = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    if is_aarch64():
        transform = Gst.ElementFactory.make("nvegltransform", "nvegl-transform")
    sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")

    # properties
    caps_v4l2src.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
    caps_vidconvsrc.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
    source.set_property('device', device)
    streammux.set_property('width', width)
    streammux.set_property('height', height)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    pgie.set_property('config-file-path', "ds_jet.txt")
    sink.set_property('sync', False)

    # add elements to pipeline
    pipeline.add(source)
    pipeline.add(caps_v4l2src)
    pipeline.add(vidconvsrc)
    pipeline.add(nvvidconvsrc)
    pipeline.add(caps_vidconvsrc)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)
    if is_aarch64():
        pipeline.add(transform)

    # link pipeline
    source.link(caps_v4l2src)
    caps_v4l2src.link(vidconvsrc)
    vidconvsrc.link(nvvidconvsrc)
    nvvidconvsrc.link(caps_vidconvsrc)

    # source pipeline
    sinkpad = streammux.get_request_pad("sink_0")
    srcpad = caps_vidconvsrc.get_static_pad("src")
    srcpad.link(sinkpad)
    streammux.link(pgie)
    pgie.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(transform)
    transform.link(sink)

    
    # this starts the video capture playing
    pipeline.set_state(Gst.State.PLAYING)
    
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)
    loop.run()
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    main(sys.argv)

