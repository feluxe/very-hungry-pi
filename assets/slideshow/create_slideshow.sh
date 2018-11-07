
convert -delay 600 slides/slide1.jpg   \
        -delay 100 slides/slide2a.jpg  \
        -delay 100 slides/slide2b.jpg  \
        -delay 100 slides/slide2c.jpg  \
        -delay 100 slides/slide2d.jpg  \
        -delay 100 slides/slide2e.jpg  \
        -delay 100 slides/slide2f.jpg  \
        -delay 100 slides/slide2g.jpg  \
        -delay 100 slides/slide2h.jpg  \
        -delay 100 slides/slide2i.jpg  \
        -delay 100 slides/slide2j.jpg  \
        -delay 100 slides/slide2k.jpg  \
        -delay 100 slides/slide2l.jpg  \
        -delay 100 slides/slide2m.jpg  \
        -delay 100 slides/slide2n.jpg  \
        -delay 600 slides/slide3.jpg   \
        -delay 600 slides/slide4.jpg   \
        -delay 600 slides/slide6.jpg   \
        -delay 600 slides/slide7.jpg   \
        -delay 600 slides/slide8.jpg   \
        -resize 768x576 \
        -layers OptimizePlus \
        -background white \
        -alpha remove \
        -loop 0 \
        slideshow.gif

