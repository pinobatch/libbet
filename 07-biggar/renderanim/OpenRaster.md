## File layout

An OpenRaster file has a name ending in `.ora`.  As described in the
[OpenRaster specification], it is a zipfile containing the following
object names:

- `mimetype`: the 16-byte string `image/openraster` (store, not
  deflate).  This string is also its Internet media type.
- `stack.xml`: Layers stack structure as described below.
- `data/layer0.png`: Must contain all and only files referred to
  by `src=` attributes in the layers stack.
- `mergedimage.png`: Result of combining all layers, as an 8- or
  16-bit per channel RGB/RGBA PNG; when targeting animated GIF
  conversion, this is the last frame.
- `Thumbnails/thumbnail.png`: `mergedimage.png` scaled to no more
  than 256 pixels on longest side, converted to 8-bit per channel
  RGB/RGBA PNG in sRGB color.

PNG images must not be interlaced.

## Layers stack

Example of a `stack.xml` file:

    <?xml version='1.0' encoding='UTF-8'?>
    <image version="0.0.3" w="300" h="177" xres="96" yres="96">
      <!--
        xres and yres are in units of pixels per 0.0254 m
        rounded to an integer
      -->
      <stack>
        <!--
          layers are written front to back, which when targeting
          GIMP's GIF optimizer means reverse time order
        -->
        <layer name="Frame 2 (1000ms)(replace)" src="data/f0002.png" x="5" y="5" />
        <layer name="Frame 1 (1000ms)(replace)" src="data/f0001.png" x="5" y="5" />
      </stack>
    </image>

[OpenRaster specification]: http://www.freedesktop.org/wiki/Specifications/OpenRaster/
