# 0.12.0 (Color Parsing)

## Release 0.12.0

### Release Summary (Color Sequence Parsing, Background Colors, and Tests)

This release features three new effects, [Highlight](../showroom.md#highlight), [LaserEtch](../showroom.md#laseretch), and
[Sweep](../showroom.md#sweep) as well as support for parsing existing color sequences from the input data. Support for background
colors has been added throughout the engine. There are many smaller changes such as improved bezier curves, custom easing
functions, and various optimizations, some of which will be detailed below.

### It's Been A While

---

It has been nearly 8 months since the last release. That's entirely due to life changes on my end that kept me away from
TTE development. I have not been able to work on TTE consistently for about six of those months. Things have settled
and I am now able to dedicate time each week to this project (and new projects). Expect more frequent updates from
now on.

### New Effects (Highlight, LaserEtch, Sweep)

---

First up, there are three new effects.

#### Highlight

The [Highlight](../effects/highlight.md) effect runs a specular highlight across the text. To best demonstrate this effect,
I will use a solid block of text.

![highlight_block_demo](../img/changeblog_media/0.12.0/highlight_block_demo.gif)

The highlight brightness, width, and direction are all customizable.

#### LaserEtch

The [LaserEtch](../effects/laseretch.md) effect burns the text into the terminal, sending sparks flying. As the sparks fall, they
cool and disappear. If the sparks reach the bottom of the canvas before burning out, they will land on the bottom.

![laseretch_demo](../img/effects_demos/laseretch_demo.gif)

The etch speed, laser colors, spark colors and all gradients are customizable.

#### Sweep

The [Sweep](../effects/sweep.md) effect makes two passes over the canvas. On the first pass, the text is revealed, dimmed, and
without color. On the second pass, the text is colored.

![sweep_demo](../img/effects_demos/sweep_demo.gif)

The sweep directions and sweep noise symbols are customizable. On the second sweep, the noise takes on colors from the final gradient.

### Color Sequence Parsing

---

TTE can now parse 8/24-bit color sequences from the input data, and associate them with the characters to which they
should be applied. This includes both foreground and background sequences.

The following ANSI escape sequence formats are supported:
: 8-bit Sequences
: - `ESC[38:5:⟨n⟩m Select foreground color`
: - `ESC[48:5:⟨n⟩m Select background color`
: 24-bit Sequences
: - `ESC[38;2;⟨r⟩;⟨g⟩;⟨b⟩ m Select RGB foreground color`
: - `ESC[48;2;⟨r⟩;⟨g⟩;⟨b⟩ m Select RGB background color`
: [Wikipedia - ANSI escape codes](https://en.wikipedia.org/wiki/ANSI_escape_code#8-bit)

---

There is a new [TerminalConfig](../engine/terminal/terminalconfig.md#terminaltexteffects.engine.terminal.TerminalConfig.existing_color_handling) command line argument `--existing-color-handling` that determines how these sequences are used within effects.

There are three options for the `--existing-color-handling` argument:

`dynamic`

: When set to 'dynamic', each effect will determine how the input sequences are handled.

`always`

: When set to 'always', no other color will be applied to the characters. They will always reflect the colors as provided
in the input text. In most cases, this setting will result in an effect that loses much of its design.

`ignore`

: When set to 'ignore', the input colors will be ignored. This is the default.

#### Color Handling Example

I recommend using a tool such as [ASCII Silhouettify](https://meatfighter.com/ascii-silhouettify/) to turn your art into ASCII.

In the example below, ASCII Silhouettify was used to process the image into ASCII with color sequences. The ASCII
was piped directly into TTE. Each of the color handling options is demonstrated.

=== "Source Image"

    ![astro_planet_balloon](../img/changeblog_media/0.12.0/astro_holding_planet.png)

=== "Resulting ASCII"

    ```
    [38;5;53m                        ___-mmma___                                               
                        _s"[38;5;222m-[38;5;214m_[38;5;222m"[38;5;214m~gggg~[38;5;222m""= [38;5;180m.[38;5;53m<-_                                          
                    _r[38;5;214m_g@@@@@@@@@@D"[38;5;166mr[38;5;214m_g@p[38;5;222m"q_[38;5;53ma                                        
                    ,f[38;5;214mg@@@@@@@@@D"[38;5;166mo"[38;5;214mo@@@@@@@P[38;5;166m,[38;5;180m"[38;5;222m_[38;5;53mo   ________                           
                /[38;5;172m,[38;5;214m@@@@@@B>[38;5;166m_="[38;5;214mg@@@@@@@@P[38;5;166m,"[38;5;214mo@@[38;5;166m_ [38;5;53m'([38;5;229m.[38;5;53m_[38;5;229m-..[38;5;221mq_ q_[38;5;53ma                         
                j[38;5;172mJ[38;5;214m{@P"[38;5;166m.="[38;5;214m<@@@@@@@@@P"[38;5;166m=[38;5;214m_g@@"[38;5;166m~"[38;5;214mg@[38;5;222m' [38;5;53m[ ][38;5;221m.[38;5;229m,[38;5;221m[@[38;5;229m,[38;5;221mjW[38;5;53m[                         
                /[38;5;172m_[38;5;130m"[38;5;166m"[38;5;214m~g@@@@@@@@@@P[38;5;166m_="[38;5;214mg@@P[38;5;166m_+[38;5;214m_@@@P[38;5;166m_@[38;5;130m.[38;5;53m]F[38;5;229m,[38;5;221m_gP gP[38;5;53mf                          
                /[38;5;172m@ [38;5;214m@@@@@@@@P"[38;5;166mo"[38;5;214m_@@@P[38;5;166m_="[38;5;214mg@@@>[38;5;166m_P'[38;5;53m_+[38;5;229m.~[38;5;221m_@"_wP[38;5;53m;                            
                .[38;5;172m.@,[38;5;214m@BP"[38;5;166m.="[38;5;214m_g@@D"[38;5;166m->[38;5;214m_g@@@>[38;5;166m_*'[38;5;53m_s"[38;5;229m,[38;5;221m__@P _@"[38;5;53mr                              
                ' [38;5;130m>"[38;5;214m_g@@@B="[38;5;166m<>[38;5;214m_g@@@B>[38;5;166m-"[38;5;130m~"[38;5;53mo"[38;5;229m_ "[38;5;221mgB"[38;5;229m~[38;5;221m_@"[38;5;53mo"                                
                ;[38;5;172mD=[38;5;130m_[38;5;214m"[38;5;166ms>"[38;5;214mo@@@@B>'[38;5;130m_->[38;5;53m_="[38;5;221m~ _g@P _gP"[38;5;53ms"@                                  
            _>t[38;5;172m"@@@_[38;5;214m<4+"[38;5;166m~[38;5;130m_w>[38;5;53m_="[38;5;229m_[38;5;221m^,_gB" _gD"[38;5;53m,>[38;5;130m_D[38;5;172m_[38;5;53m,'                                  
            -[38;5;179m_u[38;5;53m_Fo[38;5;172m"[38;5;130mgg@B>"[38;5;53mo*"[38;5;179m_[38;5;221m'[38;5;229m~[38;5;221m_g@P"[38;5;229m~[38;5;221m_gM"[38;5;53m,>[38;5;130m_d"[38;5;172mo@B"[38;5;53mF                                   
        _[38;5;179m_1@1[38;5;53m%mmP>"[38;5;179m_gy@@@@@@.__[38;5;221m~"""[38;5;53ms"[38;5;130m~8"[38;5;172m<@@P"_'[38;5;53m/                                    
        0[38;5;179mgW@@@@@@W@@@Q$@B@@@B>[38;5;53m_s"[38;5;130m_m>[38;5;172m_g@@P"_g@P[38;5;53ms                                      
        1[38;5;179m@@g5@@@@@g@@D>"[38;5;53m-="[38;5;130m_mD"[38;5;172m_g@@D>__g@@@"[38;5;53m+                                        
        '<=mmm==>""   "a_[38;5;172m4@BP>"__g@@@BP"[38;5;53mr"                                          
                            "<==mmy=""                                               
                                    ]                                                  
                                    ]                                                  
            _~~B>"""->._            ]                                                  
        ,+[38;5;231m_^[38;5;53m~[38;5;231m-"[38;5;53m_@@B==4@g_g_         ]                                                  
    ,/[38;5;231mgF[38;5;53m^[38;5;231mf[38;5;53m_@P[38;5;139m_g@BBBB@@_[38;5;53m4@@,       ]                                                  
    _[38;5;231m_@[38;5;53m,[38;5;231m/[38;5;53m_@[_~g@@@@@@@g_[38;5;139m8L[38;5;53m0@L   _~~1_                                                 
    ,[38;5;231m/@[38;5;53m,[38;5;231m/[38;5;53m/@@@@@@@@@@@@@@@@[38;5;139m'g[38;5;53mQ@\ j[38;5;231md[38;5;53m/[38;5;231m|g[38;5;53m]h                                                
    |[38;5;231m@g[38;5;53m'[38;5;231m/[38;5;53m@@@@@@@@@@@@@@@@@@[38;5;139m'[38;5;53m[@@/[38;5;231m/'.[38;5;53m<>[38;5;231m/[38;5;53m[                                                
    [38;5;231m@|.[38;5;53m:@/[38;5;139mgp[38;5;53m\@@@@@@@@@@@@@@@@@ [38;5;231m@ [38;5;53mL[38;5;146m=r[38;5;53m_'                                                
    ![38;5;231m@h[38;5;53m,[38;5;231m,[38;5;53m@[38;5;139m'@@"[38;5;53m@@@@@@@@@@@@@@@@@.[38;5;231m@@[38;5;146m'[38;5;53m]\                                                  
    ]"[38;5;231m==a[38;5;53m<)@+"@@@@@@@@@@@@@B2#F[38;5;231m@g, [38;5;53m" ',                                                
    F[38;5;231m@@@_`q[38;5;53mt\oW@BP@@@@0S$W@@'/[38;5;231mAB"[38;5;146mf[38;5;53m|    \                                               
    l[38;5;231m4@@@[38;5;146m_[38;5;53m,[38;5;231m![38;5;53mr0@@@@@@@@@@@P[38;5;146m,^[38;5;53m"[38;5;146mg+@W[38;5;53mJ                                                     
    ^[38;5;146m'@@P[38;5;53m/_<.[38;5;146m<-_[38;5;53m"""""[38;5;146m_+"[38;5;53m_"[38;5;146moF[38;5;231mg@[38;5;53m\s     _                                                
        ">_[38;5;146m"=[38;5;53m_""""_<"[38;5;146m_@"[38;5;231mg@@@@[38;5;53m`,                                                     
            ![38;5;231m![38;5;53m|[38;5;146m0@@@@BP"[38;5;231m_g@@P"[38;5;53m~"[38;5;231m:a[38;5;53mV_                                                    
            '_[38;5;231m;@@@F[38;5;146ma[38;5;231m[@@P[38;5;53m+f[38;5;231maB=4@[38;5;53m\[38;5;231m9p[38;5;53m\[                                                   
            @[38;5;231m[@@@[38;5;146m' [38;5;231m[@B[38;5;53m___[38;5;231m`[38;5;32m' [38;5;39m`[38;5;231m[[38;5;53m,[38;5;231m"[38;5;146m~ [38;5;53m,                                                   
            [[38;5;231m@@@'[38;5;53m[[38;5;231m-mm=>"[38;5;53m_'[38;5;146m'qB>[38;5;53mJ~"[38;5;231mg[38;5;53m[                                                   
            [[38;5;231m!@@[38;5;146m;[38;5;53mTR"""[38;5;146m~[38;5;231m__[38;5;53m~~[38;5;231m_g@@P'T[38;5;53m[                                                   
            |[38;5;231m[@@g_[38;5;53m"L[38;5;146mG[38;5;231m@@@@[[38;5;146mg""[38;5;53m~[38;5;146m_-[38;5;231m_@[38;5;53m[                                                   
            |[38;5;231m[@@@[38;5;53m8-"@[38;5;231m@@@@@[38;5;146mF[38;5;53m@ [38;5;146m"[38;5;231m_@@8[38;5;53m|                                                   
            {[38;5;146m:[38;5;231m"[38;5;146m_r[38;5;53m]  8[38;5;231m"==*"[38;5;53m~T[38;5;231m'*8="[38;5;53m-                                                    
                    ;[38;5;231m/@@@"[38;5;53m_ ][38;5;231m|@@+_[38;5;53m1                                                    
                    [[38;5;231m@@@@g[38;5;146m| [38;5;53m[[38;5;146m\[38;5;231m@@@@,                                                    
                    [38;5;53m![38;5;231m`@@@F[38;5;146m'  [38;5;53m\[38;5;146m*[38;5;231m"="[38;5;146m'                                                    
                    [38;5;53m".[38;5;146m""[38;5;53m_"    """                                                     
    [0m
    ```

??? example "Dynamic Color Sequence Handling"
    The beams effect supports dynamic color handling which results in the standard gradient being
    replaced with the colors parsed from the input data. The beams, however, keep their color.

    ![beams_astro_dynamic](../img/changeblog_media/0.12.0/beams_dynamic_astro_demo.gif)

??? example "Always Color Sequence Handling"
    The characters never deviate from the input colors. This results in the beams taking on the color
    of the character as they pass over. The dimming effect is not applied.

    ![beams_astro_always](../img/changeblog_media/0.12.0/beams_always_astro_demo.gif)

??? example "Ignore Color Sequence Handling"
    The color sequences are parsed and removed from the input. The result is the normal
    effect behavior.

    ![beams_astro_ignore](../img/changeblog_media/0.12.0/beams_ignore_astro_demo.gif)

Support for dynamic color handling has not been added to all effects. To track the progress of this feature, see
[this Issue](https://github.com/ChrisBuilds/terminaltexteffects/issues/37).

### Background Colors

---

TTE now supports specifying background colors throughout the engine. In calls which expect color values, a [ColorPair](../engine/utils/colorpair.md) object, providing a foreground and/or background color is used.

There are no effects currently which use background colors.

---

### Ease All The Things

*easing is easy*

#### Easing Closure

A new [easing](../engine/utils/easing.md) function is available that provides a closure around an arbitrary ease.

Example:

```python
import terminaltexteffects as tte

bounce_ease = tte.easing.eased_step_function(easing_func=tte.easing.out_bounce, 
                                             step_size=0.01)
print(bounce_ease())
print(bounce_ease())
print(bounce_ease())
print(bounce_ease())
```

Output:

```text
(0.0, 0.0)
(0.01, 0.0007562500000000001)
(0.02, 0.0030250000000000003)
(0.03, 0.00680625)
```

Every call to `bounce_ease` above, outputs a tuple of (current step, eased value). Once the current step reaches 1,
the function will stop increasing the step and the return value will never change.

The [wipe](../effects/wipe.md) effect supports arbitrary easing via this new function. Here is an example of the `out_bounce`
easing function applied to the progression of the wipe.

![bounce_wipe](../img/changeblog_media/0.12.0/wipe_bounce_demo.gif)

#### Custom Cubic Bezier Ease

In addition to the function above, a new easing function has been added which allows for the specification of completely
custom easing function using bezier control points. An example follows.

Here, I'll use [cubic-bezier.com](https://cubic-bezier.com/#0,.80,1,.20) to visually build a curve. The x-axis is time,
in our case each call to the ease function will progress one unit across the x-axis. The y-axis is the progression of the
function. The bottom is 0, the top is 1.

![cubic-bezier.com](../img/changeblog_media/0.12.0/cubic-bezier.com_demo.png)

I will apply the control points seen in the image above, (0, .81, .98, .22) to the easing function and
pass the function to the `ease` argument when creating a new [Path](../engine/motion/path.md). The target
[Coord](../engine/utils/geometry.md) will be the right side of the canvas.

```python
target_coord = tte.Coord(
    self.terminal.canvas.right,
    self.terminal.canvas.center_row,
)
pth = test_char.motion.new_path(ease=tte.easing.make_easing(0, 0.81, 0.98, 0.22), 
                                speed=0.5)
pth.new_waypoint(target_coord)
```

With the custom easing function applied to the motion of a single character traveling across the canvas, we would
expect to see the character move quickly at first, slow down towards the center, and speed up again as it progresses
to the right of the canvas.

![custom_eased_path](../img/changeblog_media/0.12.0/custom_ease_demo.gif)

### Misc Optimizations and Fixes

This updates includes many fixes and optimizations, details can be found in the full changelog.

### Testing

Now that TTE has grown in scale beyond that which I can meaningfully test manually, a full suite of unittests has been added.
Pytest is fun, and parameterization has enabled the testing of all effects, with all of their arguments, and a representative
sample of the acceptable ranges for those arguments. This was simply impossible manually. All together, there are approximately
30,000 tests run against the codebase, taking about seven minutes.
