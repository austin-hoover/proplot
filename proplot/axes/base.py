#!/usr/bin/env python3
"""
The first-level axes subclass used for all ProPlot figures.
Implements basic shared functionality.
"""
import copy
import re
from numbers import Integral

import matplotlib.axes as maxes
import matplotlib.cm as mcm
import matplotlib.colors as mcolors
import matplotlib.container as mcontainer
import matplotlib.contour as mcontour
import matplotlib.gridspec as mgridspec
import matplotlib.legend as mlegend
import matplotlib.patches as mpatches
import matplotlib.patheffects as mpatheffects
import matplotlib.projections as mprojections
import matplotlib.text as mtext
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib import cbook

from .. import colors as pcolors
from .. import constructor
from .. import gridspec as pgridspec
from ..config import _parse_format, _translate_loc, rc
from ..internals import ic  # noqa: F401
from ..internals import (
    _guide_kw_from_obj,
    _keyword_to_positional,
    _not_none,
    _pop_kwargs,
    _pop_params,
    _pop_props,
    _snippet_manager,
    _version_mpl,
    docstring,
    rcsetup,
    warnings,
)
from ..utils import _fontsize_to_pt, edges, to_rgb, units

try:
    from cartopy.crs import CRS, PlateCarree
except Exception:
    CRS = PlateCarree = object

__all__ = ['Axes']


# A-b-c label string
ABC_STRING = 'abcdefghijklmnopqrstuvwxyz'


# Transform docstring
# Used for text and add_axes
_transform_docstring = """
transform : {'data', 'axes', 'figure'} or `~matplotlib.transforms.Transform`, optional
    The transform used to interpret the bounds. Can be a
    `~matplotlib.transforms.Transform` instance
    or a string representing the `~matplotlib.axes.Axes.transData`,
    `~matplotlib.axes.Axes.transAxes`, or `~matplotlib.figure.Figure.transFigure`
    transforms. Default is ``'axes'``, i.e. `bounds` is in axes-relative coordinates.
"""
_snippet_manager['axes.transform'] = _transform_docstring


# Projection docstring
_proj_docstring = """
proj, projection : \
str, `cartopy.crs.Projection`, or `~mpl_toolkits.basemap.Basemap`, optional
    The map projection specification(s). If ``'cart'`` or ``'cartesian'``
    (the default), a `~proplot.axes.CartesianAxes` is created. If ``'polar'``,
    a `~proplot.axes.PolarAxes` is created. Otherwise, the argument is
    interpreted by `~proplot.constructor.Proj`, and the result is used
    to make a `~proplot.axes.GeoAxes` (in this case the argument can be
    a `cartopy.crs.Projection` instance, a `~mpl_toolkits.basemap.Basemap`
    instance, or a projection name listed in :ref:`this table <proj_table>`).
"""
_proj_kw_docstring = """
proj_kw, projection_kw : dict-like, optional
    Keyword arguments passed to `~mpl_toolkits.basemap.Basemap` or
    cartopy `~cartopy.crs.Projection` classes on instantiation.
"""
_basemap_docstring = """
basemap : bool or dict-like, optional
    Whether to use `~mpl_toolkits.basemap.Basemap` or `~cartopy.crs.Projection`
    for map projections. Default is :rc:`basemap`.
"""
_snippet_manager['axes.proj'] = _proj_docstring
_snippet_manager['axes.proj_kw'] = _proj_kw_docstring
_snippet_manager['axes.basemap'] = _basemap_docstring


# Inset docstring
_inset_docstring = """
Return an inset `CartesianAxes`. This is similar to the builtin
`~matplotlib.axes.Axes.inset_axes` but includes some extra options.

Parameters
----------
bounds : 4-tuple of float
    The (left, bottom, width, height) coordinates for the axes.
%(axes.transform)s
    Default is to use the same projection as the current axes.
%(axes.proj)s
%(axes.proj_kw)s
%(axes.basemap)s
zorder : float, optional
    The `zorder <https://matplotlib.org/stable/gallery/misc/zorder_demo.html>`__
    of the axes, should be greater than the zorder of elements in the parent
    axes. Default is ``4``.
zoom : bool, optional
    Whether to draw lines indicating the inset zoom using
    `~Axes.indicate_inset_zoom`. The lines will automatically
    adjust whenever the parent axes or inset axes limits are
    changed. Default is ``True``.
zoom_kw : dict, optional
    Passed to `~Axes.indicate_inset_zoom`.

Other parameters
----------------
**kwargs
    Passed to `CartesianAxes`.
"""
_snippet_manager['axes.inset'] = _inset_docstring


# Panel docstring
_panel_docstring = """
Return a panel drawn along the edge of this axes.

Parameters
----------
side : str, optional
    The panel location. The following location keys are valid:

    ==========  =====================
    Location    Valid keys
    ==========  =====================
    left        ``'left'``, ``'l'``
    right       ``'right'``, ``'r'``
    bottom      ``'bottom'``, ``'b'``
    top         ``'top'``, ``'t'``
    ==========  =====================

width : float or str, optional
    The panel width. Default is :rc:`subplots.panelwidth`.
    %(units.in)s
space : float or str, optional
    The fixed space between the main subplot and the panel.
    %(units.em)s
    When the tight layout algorithm is active for the figure, this is adjusted
    automatically using `pad`. Otherwise, a suitable default is selected.
pad : float or str, optional
    The tight layout padding between the main subplot and the panel. Units are
    interpreted by `~proplot.utils.units`. Default is :rc:`subplots.panelpad`.
share : bool, optional
    Whether to enable axis sharing between the *x* and *y* axes of the
    main subplot and the panel long axes for each panel in the stack.
    Sharing between the panel short axis and other panel short axes
    is determined by figure-wide `sharex` and `sharey` settings.

Returns
-------
`~proplot.axes.CartesianAxes`
    The panel axes.
"""
_snippet_manager['axes.panel'] = _panel_docstring


# Colorbar and legend space
_space_docstring = """
space : float or str, optional
    For outer {name}s only. The fixed space between the {name} and the main axes.
    %(units.em)s
    When the tight layout algorithm is active for the figure, this is adjusted
    automatically using `pad`. Otherwise, a suitable default is selected.
pad : float or str, optional
    The padding between the axes edge and the {name}. For outer {name}s, this is the
    tight layout padding. Default is :rc:`subplots.panelpad`. For inset {name}s, this
    is the fixed space between the axes edge and the {name}. Default is :rc:`{default}`.
    %(units.em)s
queue : bool, optional
    If ``True`` and `loc` is the same as an existing {name}, the input
    arguments are added to a queue and this function returns ``None``.
    This is used to "update" the same {name} with successive ``ax.{name}(...)``
    calls. If ``False`` (the default) and `loc` is the same as an existing
    *inset* {name}, the old {name} is removed. If ``False`` and `loc` is an
    *outer* {name}, the {name}s are stacked.
"""
_snippet_manager['axes.legend_space'] = _space_docstring.format(
    name='legend', default='legend.borderaxespad'
)
_snippet_manager['axes.colorbar_space'] = _space_docstring.format(
    name='colorbar', default='colorbar.insetpad'
)


# Format docstrings
_axes_format_docstring = """
title : str, optional
    The axes title.
abc : bool or str, optional
    The "a-b-c" subplot label style. Must contain the character ``a`` or ``A``,
    for example ``'a.'``, or ``'A'``. If ``True`` then the default style of
    ``'a'`` is used. The ``a`` or ``A`` is replaced with the alphabetic character
    matching the `~Axes.number`. If `~Axes.number` is greater than 26, the
    characters loop around to a, ..., z, aa, ..., zz, aaa, ..., zzz, etc.
abcloc, titleloc : str, optional
    Strings indicating the location for the a-b-c label and main title.
    The following locations are valid (defaults are :rc:`abc.loc` and
    :rc:`title.loc`):

    .. _title_table:

    ========================  ============================
    Location                  Valid keys
    ========================  ============================
    center above axes         ``'center'``, ``'c'``
    left above axes           ``'left'``, ``'l'``
    right above axes          ``'right'``, ``'r'``
    lower center inside axes  ``'lower center'``, ``'lc'``
    upper center inside axes  ``'upper center'``, ``'uc'``
    upper right inside axes   ``'upper right'``, ``'ur'``
    upper left inside axes    ``'upper left'``, ``'ul'``
    lower left inside axes    ``'lower left'``, ``'ll'``
    lower right inside axes   ``'lower right'``, ``'lr'``
    ========================  ============================

abcborder, titleborder : bool, optional
    Whether to draw a white border around titles and a-b-c labels positioned
    inside the axes. This can help them stand out on top of artists plotted
    inside the axes. Defaults are :rc:`abc.border` and :rc:`title.border`.
abcbbox, titlebbox : bool, optional
    Whether to draw a white bbox around titles and a-b-c labels positioned
    inside the axes. This can help them stand out on top of artists plotted
    inside the axes. Defaults are :rc:`abc.bbox` and :rc:`title.bbox`.
abc_kw, title_kw : dict-like, optional
    Additional settings used to update the a-b-c label and title
    with ``text.update()``.
titlepad : float, optional
    The padding for the inner and outer titles and a-b-c labels in
    arbitrary units (default is points). Default is :rc:`title.pad`.
titleabove : bool, optional
    Whether to try to put outer titles and a-b-c labels above panels,
    colorbars, or legends that are above the axes. Default is :rc:`title.above`.
abctitlepad : float, optional
    The horizontal padding between the a-b-c label and title when they are
    in the same location. Default is :rc:`abc.titlepad`.
ltitle, ctitle, rtitle, ultitle, uctitle, urtitle, lltitle, lctitle, lrtitle \
: str, optional
    Additional titles in specific positions. This works as an alternative
    to the ``ax.format(title='Title', titleloc=loc)`` workflow and permits
    adding more than one title-like label to a single axes.
a, alpha, fc, facecolor, ec, edgecolor, lw, linewidth, ls, linestyle : optional
    Additional settings applied to the background patch, and their shorthands.
    Defaults are :rcraw:`axes.alpha`, :rcraw:`axes.facecolor`,
    :rcraw:`axes.edgecolor`, :rcraw:`axes.linewidth`, and ``'-'``, respectively.
"""
_figure_format_docstring = """
rowlabels, collabels, llabels, tlabels, rlabels, blabels
    Aliases for `leftlabels` and `toplabels`, and for `leftlabels`,
    `toplabels`, `rightlabels`, and `bottomlabels`, respectively.
leftlabels, toplabels, rightlabels, bottomlabels : list of str, optional
    Labels for the subplots lying along the left, top, right, and
    bottom edges of the figure. The length of each list must match
    the number of subplots along the corresponding edge.
leftlabelpad, toplabelpad, rightlabelpad, bottomlabelpad : float, optional
    The padding between the labels and the axes content in arbitrary units
    (default is points). Defaults are :rcraw:`leftlabel.pad`,
    :rcraw:`toplabel.pad`, :rcraw:`rightlabel.pad`, and :rcraw:`bottomlabel.pad`
leftlabels_kw, toplabels_kw, rightlabels_kw, bottomlabels_kw : dict-like, optional
    Additional settings used to update the labels with ``text.update()``.
figtitle
    Alias for `suptitle`.
suptitle : str, optional
    The figure "super" title, centered between the left edge of
    the lefmost column of subplots and the right edge of the rightmost
    column of subplots, and automatically offset above figure titles.
    This is an improvement on matplotlib's "super" title, which just
    centers the text between figure edges.
suptitlepad : float, optional
    The padding between the super title and the axes content in arbitrary
    units (default is points). Default is :rcraw:`suptitle.pad`.
suptitle_kw : optional
    Additional settings used to update the super title with ``text.update()``.
"""
_rc_format_docstring = """
rc_mode : int, optional
    The context mode passed to `~proplot.config.Configurator.context`.
rc_kw : dict-like, optional
    An alternative to passing extra keyword arguments. See below.
**kwargs
    Passed to `proplot.config.Configurator.context` and used to update the
    axes-relevant `~proplot.config.rc` settings. For example, ``abcstyle='A.'``
    modifies the :rcraw:`abc.style` setting, ``titleloc='left'`` modifies the
    :rcraw:`title.loc` setting, ``gridminor=True`` modifies the :rcraw:`gridminor`
    setting, and ``gridbelow=True`` modifies the :rcraw:`grid.below` setting.
    Many of the keyword arguments documented above are actually applied by updating
    the `~proplot.config.rc` settings then retrieving the updated settings.
"""
_snippet_manager['axes.rc'] = _rc_format_docstring
_snippet_manager['axes.format'] = _axes_format_docstring
_snippet_manager['figure.format'] = _figure_format_docstring


# Colorbar docstrings
_colorbar_args_docstring = """
mappable : mappable, list of artists, list of color-spec, or colormap-spec
    There are four options here:

    1. A mappable object. Basically, any object with a ``get_cmap`` method,
       like the objects returned by `~matplotlib.axes.Axes.contourf` and
       `~matplotlib.axes.Axes.pcolormesh`.
    2. A list of matplotlib artists. Any object with a ``get_color`` method
       will do, like `~matplotlib.lines.Line2D` instances. A colormap will
       be generated from the colors of these objects, and colorbar levels
       will be selected using `values`.  If `values` is ``None``, we try
       to infer them by converting the handle labels returned by
       `~matplotlib.artist.Artist.get_label` to `float`. Otherwise, it is
       set to ``np.linspace(0, 1, len(mappable))``.
    3. A list of hex strings, color string names, or RGB tuples. A colormap
       will be generated from these colors, and colorbar levels will be
       selected using `values`. If `values` is ``None``, it is set to
       ``np.linspace(0, 1, len(mappable))``.
    4. A `~matplotlib.colors.Colormap` instance. In this case, a colorbar
       will be drawn using this colormap and with levels determined by
       `values`. If `values` is ``None``, it is set to
       ``np.linspace(0, 1, cmap.N)``.

values : list of float, optional
    Ignored if `mappable` is a mappable object. This maps each color or
    plot handle in the `mappable` list to numeric values, from which a
    colormap and normalizer are constructed.
"""
_colorbar_kwargs_docstring = """
extend : {None, 'neither', 'both', 'min', 'max'}, optional
    Direction for drawing colorbar "extensions" (i.e. references to
    out-of-bounds data with a unique color). These are triangles by
    default. If ``None``, we try to use the ``extend`` attribute on the
    mappable object. If the attribute is unavailable, we use ``'neither'``.
extendsize : float or str, optional
    The length of the colorbar "extensions" in physical units. Default is
    :rc:`colorbar.insetextend` for inset colorbars and :rc:`colorbar.extend` for
    outer colorbars. %(units.em)s
frame, frameon : bool, optional
    For inset colorbars only. Indicates whether to draw a "frame", just
    like `~matplotlib.axes.Axes.legend`. Default is :rc:`colorbar.frameon`.
lw, linewidth, ec, edgecolor : optional
    Controls the line width and edge color for the colorbar outline and
    dividers. For inset colorbars, also controls frame properties.
a, alpha, framealpha, fc, facecolor, framecolor : optional
    For inset colorbars only. Controls the transparency and color of the frame.
    Defaults are :rc:`colorbar.framealpha` and :rc:`colorbar.framecolor`.
norm : normalizer spec, optional
    Ignored if `values` is ``None``. The normalizer for converting `values`
    to colormap colors. Passed to `~proplot.constructor.Norm`.
norm_kw : dict-like, optional
    The normalizer settings. Passed to `~proplot.constructor.Norm`.
reverse : bool, optional
    Whether to reverse the direction of the colorbar.
tickloc, ticklocation : {'bottom', 'top', 'left', 'right'}, optional
    Where to draw tick marks on the colorbar.
tickdir, tickdirection : {'out', 'in', 'inout'}, optional
    Direction that major and minor tick marks point.
tickminor : bool, optional
    Whether to add minor ticks to the colorbar with
    `~matplotlib.colorbar.ColorbarBase.minorticks_on`.
grid, edges, drawedges : bool, optional
    Whether to draw edges (i.e., gridlines) between each level of the colorbar.
    Default is :rc:`colorbar.grid`.
label, title : str, optional
    The colorbar label. The `title` keyword is also accepted for
    consistency with `~matplotlib.axes.Axes.legend`.
locator, ticks : locator spec, optional
    Used to determine the colorbar tick positions. Passed to the
    `~proplot.constructor.Locator` constructor function.
locator_kw : dict-like, optional
    The locator settings. Passed to `~proplot.constructor.Locator`.
maxn : int, optional
    Used if `locator` is ``None``. Determines the maximum number of levels that
    are ticked. Default depends on the colorbar length relative to the font size.
    The name `maxn` is meant to be reminiscent of `~matplotlib.ticker.MaxNLocator`.
minorlocator, minorticks
    As with `locator`, `ticks` but for the minor ticks.
minorlocator_kw
    As with `locator_kw`, but for the minor ticks.
maxn_minor
    As with `maxn`, but for the minor ticks.
format, formatter, ticklabels : formatter spec, optional
    The tick label format. Passed to the `~proplot.constructor.Formatter`
    constructor function.
formatter_kw : dict-like, optional
    The formatter settings. Passed to `~proplot.constructor.Formatter`.
rotation : float, optional
    The tick label rotation. Default is ``0``.
labelsize, labelweight, labelcolor : optional
    The font size, weight, and color for colorbar label text.
ticklabelsize, ticklabelweight, ticklabelcolor : optional
    The font size, weight, and color for colorbar tick labels.
orientation : {None, 'horizontal', 'vertical'}, optional
    The colorbar orientation. By default this depends on the "side" of the subplot
    or figure where the colorbar is drawn. Inset colorbars are always horizontal.
rasterize : bool, optional
    Whether to rasterize the colorbar solids. The matplotlib default is ``True``
    but we change this to :rcraw:`colorbar.rasterize` because rasterization can
    cause misalignment between `edges` and the level patches.
**kwargs
    Passed to `~matplotlib.figure.Figure.colorbar`.
"""
_snippet_manager['axes.colorbar_args'] = _colorbar_args_docstring
_snippet_manager['axes.colorbar_kwargs'] = _colorbar_kwargs_docstring


# Legend docstrings
_legend_args_docstring = """
handles : list of `~matplotlib.artist.Artist`, optional
    List of matplotlib artists, or a list of lists of artist instances (see
    the `center` keyword). If ``None``, the artists are retrieved with
    `~matplotlib.axes.Axes.get_legend_handles_labels`.
labels : list of str, optional
    Matching list of string labels or ``None`` placeholders, or a matching list of
    lists (see the `center` keyword). Wherever ``None`` appears in the list (or if no
    labels were passed at all), labels are retrieved by calling
    `~matplotlib.artist.Artist.get_label` on each `~matplotlib.artist.Artist` in the
    handle list. If a handle consists of a tuple group of artists, labels are
    inferred from the artists in the tuple. If there are multiple unique labels in
    the tuple group of artists, the tuple group is expanded into unique legend
    entries. For details on matplotlib legend handlers, see the matplotlib
    `legend guide \
<https://matplotlib.org/stable/tutorials/intermediate/legend_guide.html>`__.
"""
_legend_kwargs_docstring = """
frame, frameon : bool, optional
    Toggles the legend frame. For centered-row legends, a frame
    independent from matplotlib's built-in legend frame is created.
ncol, ncols : int, optional
    The number of columns. `ncols` is an alias, added
    for consistency with `~matplotlib.pyplot.subplots`.
order : {'C', 'F'}, optional
    Whether legend handles are drawn in row-major (``'C'``) or column-major
    (``'F'``) order. Analagous to `numpy.array` ordering. Default is ``'F'``.
center : bool, optional
    Whether to center each legend row individually. If ``True``, we draw
    successive single-row legends stacked on top of each other. If ``None``,
    we infer this setting from `handles`. By default, `center` is set to ``True``
    if `handles` is a list of lists (each sublist is used as a row in the legend).
alphabetize : bool, optional
    Whether to alphabetize the legend entries according to the legend labels.
    Default is ``False``.
title, label : str, optional
    The legend title. The `label` keyword is also accepted, for consistency
    with `~matplotlib.figure.Figure.colorbar`.
fontsize, fontweight, fontcolor : optional
    The font size, weight, and color for the legend text. Font size is interpreted
    by `~proplot.utils.units`. The default font size is :rcraw:`legend.fontsize`.
titlefontsize, titlefontweight, titlefontcolor : optional
    The font size, weight, and color for the legend title. Font size is interpreted
    by `~proplot.utils.units`. The default size is `fontsize`.
a, alpha, framealpha, fc, facecolor, framecolor, ec, edgecolor, ew, edgewidth : optional
    The opacity, face color, edge color, and edge width for the legend frame.
    Defaults are :rc:`legend.framealpha`, :rc:`legend.facecolor`,
    :rc:`legend.edgecolor` and :rc:`axes.linewidth`.
color, lw, linewidth, m, marker, ls, linestyle, dashes, ms, markersize \
: property-spec, optional
    Properties used to override the legend handles. For example, for a
    legend describing variations in line style ignoring variations in color, you
    might want to use ``color='k'``.
borderpad, borderaxespad, handlelength, handleheight, handletextpad, \
labelspacing, columnspacing : float or str, optional
    Native `~matplotlib.axes.Axes.legend` spacing arguments interpreted with
    `~proplot.utils.units`. The default units are still font size-relative.
**kwargs
    Passed to `~matplotlib.axes.Axes.legend`.
"""
_snippet_manager['axes.legend_args'] = _legend_args_docstring
_snippet_manager['axes.legend_kwargs'] = _legend_kwargs_docstring


class Axes(maxes.Axes):
    """
    The lowest-level `~matplotlib.axes.Axes` subclass used by proplot.
    Implements basic universal features.
    """
    def __repr__(self):  # override matplotlib
        # Show the position in the geometry excluding panels. Panels are
        # indicated by showing their parent geometry plus a 'side' argument.
        ax = self._get_topmost_axes()
        try:
            nrows, ncols, num1, num2 = ax.get_subplotspec()._get_subplot_geometry()
            params = {'nrows': nrows, 'ncols': ncols, 'index': (num1, num2)}
        except (IndexError, ValueError, AttributeError):  # e.g. a panel axes
            left, bottom, width, height = np.round(self._position.bounds, 2)
            params = {'left': left, 'bottom': bottom, 'size': (width, height)}
        if self.number:
            params['number'] = self.number
        name = type(self).__name__
        if self._panel_side:
            name = name.replace('Subplot', 'Panel')  # e.g. CartesianAxesPanel
            params['side'] = self._panel_side
        for package in ('cartopy', 'basemap'):
            head = '_' + package.title()
            if head in name:  # e.g. _CartopyAxeSubplot to GeoAxesSubplot
                name = name.replace(head, 'Geo')
                params['backend'] = package
        params = ', '.join(f'{key}={value!r}' for key, value in params.items())
        return f'{name}({params})'

    def __str__(self):  # override matplotlib
        return self.__repr__()

    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        *args, **kwargs
            Passed to `~matplotlib.axes.Axes`.

        See also
        --------
        matplotlib.axes.Axes
        proplot.axes.PlotAxes
        proplot.axes.CartesianAxes
        proplot.axes.PolarAxes
        proplot.axes.GeoAxes
        """
        # Initialize parent after removing args
        # NOTE: These are really "subplot" features so documented on add_subplot().
        ss = kwargs.pop('_subplot_spec', None)  # see below
        number = kwargs.pop('number', None)
        autoshare = kwargs.pop('autoshare', None)
        autoshare = _not_none(autoshare, True)
        super().__init__(*args, **kwargs)

        # Varous scalar properties
        self._active_cycle = rc['axes.prop_cycle']
        self._auto_format = None  # manipulated by wrapper functions
        self._abc_border_kwargs = {}
        self._abc_loc = None
        self._abc_title_pad = rc['abc.titlepad']
        self._title_above = rc['title.above']
        self._title_border_kwargs = {}  # title border properties
        self._title_loc = None
        self._title_pad = rc['title.pad']
        self._title_pad_current = None
        self._altx_parent = None  # for cartesian axes only
        self._alty_parent = None
        self._inset_parent = None
        self._inset_zoom = False
        self._inset_zoom_data = None
        self._panel_hidden = False  # True when "filled" with cbar/legend
        self._panel_parent = None
        self._panel_share = False
        self._panel_sharex_group = False
        self._panel_sharey_group = False
        self._panel_side = None
        self._tight_bbox = None  # bounding boxes are saved
        self.xaxis.isDefault_minloc = True  # ensure enabled at start (needed for dual)
        self.yaxis.isDefault_minloc = True

        # Various dictionary properties
        # NOTE: Critical to use self.text() so they are patched with _update_text
        self._legend_dict = {}
        self._colorbar_dict = {}
        d = self._panel_dict = {}
        d['left'] = []  # NOTE: panels will be sorted inside-to-outside
        d['right'] = []
        d['bottom'] = []
        d['top'] = []
        d = self._title_dict = {}
        ta = self.transAxes
        d['abc'] = self.text(0, 0, '', transform=ta)
        d['left'] = self._left_title  # WARNING: track in case mpl changes this
        d['center'] = self.title
        d['right'] = self._right_title
        d['upper left'] = self.text(0, 0, '', va='top', ha='left', transform=ta)
        d['upper center'] = self.text(0, 0, '', va='top', ha='center', transform=ta)
        d['upper right'] = self.text(0, 0, '', va='top', ha='right', transform=ta)
        d['lower left'] = self.text(0, 0, '', va='bottom', ha='left', transform=ta)
        d['lower center'] = self.text(0, 0, '', va='bottom', ha='center', transform=ta)
        d['lower right'] = self.text(0, 0, '', va='bottom', ha='right', transform=ta)

        # Subplot-specific settings
        # NOTE: Default number for any axes is None (i.e., no a-b-c labels allowed)
        # and for subplots added with add_subplot is provided by fig._next_number.
        # WARNING: For mpl>=3.4.0 subplotspec assigned *after* initialization using
        # set_subplotspec. Tried to defer to setter but really messes up both format()
        # and _auto_share(). Instead use workaround: Have Figure.add_subplot pass
        # subplotspec as a hidden keyword arg. Non-subplots don't need this arg.
        # See https://github.com/matplotlib/matplotlib/pull/18564
        self._number = None
        if number:  # not None or False
            self.number = number  # documented in add_subplot
        if ss is not None:
            self.set_subplotspec(ss)
        if autoshare:
            self._auto_share()

        # Default formatting
        # NOTE: rc_mode == 1 applies the proplot settings. This is necessary
        # just on the first run. Default calls to format() use rc_mode == 2
        self.format(rc_mode=1)  # 1 applies the custom proplot params

    @staticmethod
    def _axisbelow_to_zorder(axisbelow):
        """
        Get the zorder for an axisbelow setting.
        """
        if axisbelow is True:
            zorder = 0.5
        elif axisbelow is False:
            zorder = 2.5
        elif axisbelow in ('line', 'lines'):
            zorder = 1.5
        else:
            raise ValueError(f'Unexpected axisbelow value {axisbelow!r}.')
        return zorder

    def _get_share_axes(self, x, panels=False):
        """
        Return the axes whose horizontal or vertical extent in the main gridspec
        matches the horizontal or vertical extent of this axes.
        """
        # NOTE: The lefmost or bottommost axes are at the start of the list.
        if not isinstance(self, maxes.SubplotBase):
            return [self]
        y = 'y' if x == 'x' else 'x'
        idx = 0 if x == 'x' else 1
        argfunc = np.argmax if x == 'x' else np.argmin
        irange = self._range_subplotspec(x)
        axs = self.figure._iter_axes(hidden=False, children=False, panels=panels)
        axs = [ax for ax in axs if ax._range_subplotspec(x) == irange]
        axs = list({self, *axs})  # self may be missing during initialization
        pax = axs.pop(argfunc([ax._range_subplotspec(y)[idx] for ax in axs]))
        return [pax, *axs]  # return with leftmost or bottommost first

    def _get_span_axes(self, side, panels=False):
        """
        Return the axes whose left, right, top, or bottom sides abutt against
        the same row or column as this axes. Deflect to shared panels.
        """
        if side not in ('left', 'right', 'bottom', 'top'):
            raise ValueError(f'Invalid side {side!r}.')
        if not isinstance(self, maxes.SubplotBase):
            return [self]
        x, y = 'xy' if side in ('left', 'right') else 'yx'
        idx = 0 if side in ('left', 'top') else 1  # which side to test
        coord = self._range_subplotspec(x)[idx]  # side for a particular axes
        axs = self.figure._iter_axes(hidden=False, children=False, panels=panels)
        axs = [ax for ax in axs if ax._range_subplotspec(x)[idx] == coord] or [self]
        out = []
        for ax in axs:
            other = getattr(ax, '_share' + y)
            if other and other._panel_parent:  # this is a shared panel
                ax = other
            out.append(ax)
        return out

    def _get_topmost_axes(self):
        """
        Return the "main" subplot associated with this axes. Try a few levels.
        """
        # NOTE: Not trivial because panels can't be children of their 'main'
        # subplots. So have to loop to parent of panel, then main subplot, etc.
        for _ in range(5):
            self = self._axes or self
            self = self._altx_parent or self
            self = self._inset_parent or self
            self = self._panel_parent or self
        return self

    @staticmethod
    def _get_background_props(patch_kw=None, context=True, **kwargs):
        """
        Return boundary properties. Backgrounds are used in all axes projections.
        """
        # Deprecated behavior
        if patch_kw:
            warnings._warn_proplot(
                "Keyword 'patch_kw' was deprecated in v0.8. Please pass "
                'patch properties as keyword arguments instead.'
            )
            kwargs.update(patch_kw)

        # Get user-input properties and changed rc settings
        # NOTE: Here we use 'color' as an alias for just 'edgecolor' rather than
        # both 'edgecolor' and 'facecolor' to match 'xcolor' and 'ycolor' arguments.
        props = _pop_props(kwargs, 'patch')
        for key in ('alpha', 'facecolor', 'linewidth', 'edgecolor'):
            value = rc.find('axes.' + key, context=context)
            if value is not None:
                props.setdefault(key, value)

        # Partition properties into face and edge
        kw_face = _pop_kwargs(props, 'alpha', 'facecolor')
        kw_edge = _pop_kwargs(props, 'edgecolor', 'linewidth', 'linestyle')
        kw_edge['capstyle'] = 'projecting'  # NOTE: needed to fix cartopy bounds
        if 'color' in props:
            kw_edge.setdefault('edgecolor', props.pop('color'))
        if kwargs:
            raise TypeError(f'Unexpected keyword argument(s): {kwargs!r}')

        return kw_face, kw_edge

    def _get_gridline_props(self, native=False, which='major', context=True):
        """
        Return gridline properties. Gridlines are used in all axes projections.
        """
        # Line properties
        # NOTE: Gridline zorder is controlled automatically by matplotlib but
        # must be controlled manually for geographic projections
        key = 'grid' if which == 'major' else 'gridminor'
        prefix = 'grid_' if native else ''  # for native gridlines use this prefix
        kwlines = rc.fill(
            {
                f'{prefix}alpha': f'{key}.alpha',
                f'{prefix}color': f'{key}.color',
                f'{prefix}linewidth': f'{key}.linewidth',
                f'{prefix}linestyle': f'{key}.linestyle',
            },
            context=context,
        )
        axisbelow = rc.find('axes.axisbelow', context=context)
        if axisbelow is not None:
            if native:  # this is a native plot so use built-in method
                self.set_axisbelow(axisbelow)
            else:  # this is a geographic plot so apply with zorder
                kwlines['zorder'] = self._axisbelow_to_zorder(axisbelow)
        return kwlines

    @staticmethod
    def _get_gridline_toggle(grid=None, axis=None, which='major', context=True):
        """
        Get the major and minor gridline toggles for the axis.
        """
        # NOTE: If you pass 'grid' or 'gridminor' the native args are updated
        # NOTE: Very careful to return not None only if setting was changed.
        # Avoid unnecessarily triggering grid redraws (esp. bad for geo.py)
        grid_on = rc.find('axes.grid', context=context)
        which_on = rc.find('axes.grid.which', context=context)
        if grid_on is not None or which_on is not None:  # if *one* was changed
            axis_on = rc['axes.grid.axis']  # always need this property
            grid_on = _not_none(grid_on, rc['axes.grid'])
            which_on = _not_none(which_on, rc['axes.grid.which'])
            axis = _not_none(axis, 'x')
            axis_on = axis is None or axis_on in (axis, 'both')
            which_on = which_on in (which, 'both')
            grid = _not_none(grid, grid_on and axis_on and which_on)

        return grid

    @staticmethod
    def _get_label_props(**kwargs):
        """
        Retrieve the axis label properties.
        """
        # Get the rc settings
        # NOTE: This permits passing arbitrary additoinal args to set_[xy]label()
        kw = rc.fill(
            {
                'color': 'axes.labelcolor',
                'weight': 'axes.labelweight',
                'size': 'axes.labelsize',
                'family': 'font.family',
                'labelpad': 'axes.labelpad',  # read by set_xlabel/set_ylabel
            },
            context=True,
        )
        for key, value in kwargs.items():
            if value is not None:  # allow e.g. color=None
                kw[key] = value
        return kw

    @staticmethod
    def _get_loc(x, string):
        """
        Convert the boolean "left", "right", "top", and "bottom" spine or tick rc
        settings to a location string. Returns ``None`` if settings are unchanged.
        """
        opt1, opt2 = ('top', 'bottom') if x == 'x' else ('left', 'right')
        b1 = rc.find(f'{string}.{opt1}', context=True)
        b2 = rc.find(f'{string}.{opt2}', context=True)
        if b1 is None and b2 is None:
            return None
        elif b1 and b2:
            return 'both'
        elif b1:
            return opt1
        elif b2:
            return opt2
        else:
            return 'neither'

    @staticmethod
    def _get_ticklabel_props(axis=None, context=True):
        """
        Return tick or grid label properties.
        """
        # NOTE: 'tick.label' properties are now synonyms of 'grid.label' properties
        sprefix = axis or ''
        cprefix = sprefix if _version_mpl >= 3.4 else ''  # newly introduced setting
        kwtext = rc.fill(
            {
                'color': f'{cprefix}tick.labelcolor',  # native setting sometimes avail
                'size': f'{sprefix}tick.labelsize',  # native setting always avail
                'weight': 'tick.labelweight',  # native setting never avail
                'family': 'font.family',  # apply manually
            },
            context=context,
        )
        if kwtext.get('color', None) == 'inherit':
            # Inheritence is not automatic for geographic
            # gridline labels so we apply inheritence here.
            kwtext['color'] = rc[f'{sprefix}tick.color']
        return kwtext

    @staticmethod
    def _get_tick_props(axis=None, which='major'):
        """
        Return tick properties.
        """
        # Tick properties obtained with rc.category
        # NOTE: This loads 'size', 'width', 'pad', 'bottom', and 'top'
        axis = _not_none(axis, 'x')
        kwticks = rc.category(axis + 'tick.' + which, context=True)
        kwticks.pop('visible', None)
        return kwticks

    def _get_size_inches(self):
        """
        Return the width and height of the axes in inches.
        """
        width, height = self.figure.get_size_inches()
        bbox = self.get_position()
        width = width * abs(bbox.width)
        height = height * abs(bbox.height)
        return np.array([width, height])

    def _get_transform(self, transform, default='data'):
        """
        Translates user input transform. Also used in an axes method.
        """
        # TODO: Can this support cartopy transforms? Seems not when this
        # is used for inset axes bounds but maybe in other places?
        transform = _not_none(transform, default)
        if isinstance(transform, mtransforms.Transform):
            return transform
        elif CRS is not object and isinstance(transform, CRS):
            return transform
        elif PlateCarree is not object and transform == 'map':
            return PlateCarree()
        elif transform == 'figure':
            return self.figure.transFigure
        elif transform == 'axes':
            return self.transAxes
        elif transform == 'data':
            return self.transData
        else:
            raise ValueError(f'Unknown transform {transform!r}.')

    def _hide_panel(self):
        """
        Hide axes contents but do *not* make the entire axes invisible. This is used to
        fill "panels" surreptitiously added to the gridspec for the purpose of drawing
        outer colorbars and legends.
        """
        # WARNING: Do not use self.clear in case we want to add a subplot
        # title or a-b-c label above a colorbar or legend in a top panel
        for s in self.spines.values():
            s.set_visible(False)
        self.xaxis.set_visible(False)
        self.yaxis.set_visible(False)
        self.patch.set_alpha(0)
        self.patch.set_facecolor('none')
        self._panel_hidden = True

    def _make_inset_locator(self, bounds, trans):
        """
        Return a locator that determines inset axes bounds.
        """
        def _inset_locator(ax, renderer):
            bbox = mtransforms.Bbox.from_bounds(*bounds)
            bb = mtransforms.TransformedBbox(bbox, trans)
            tr = self.figure.transFigure.inverted()
            bb = mtransforms.TransformedBbox(bb, tr)
            return bb
        return _inset_locator

    def _range_subplotspec(self, x):
        """
        Return the column or row range for the subplootspec.
        """
        if not isinstance(self, maxes.SubplotBase):
            raise RuntimeError('Axes must be a subplot.')
        ss = self.get_subplotspec()
        row1, row2, col1, col2 = ss._get_rows_columns()
        if x == 'x':
            return (col1, col2)
        else:
            return (row1, row2)

    def _range_tightbbox(self, x):
        """
        Return the tight bounding box span from the cached bounding box.
        """
        # TODO: Better testing for axes visibility
        bbox = self._tight_bbox
        if bbox is None:
            return np.nan, np.nan
        if x == 'x':
            return bbox.xmin, bbox.xmax
        else:
            return bbox.ymin, bbox.ymax

    def _sharex_setup(self, sharex):
        """
        Configure x-axis sharing for panels. See also `~CartesianAxes._sharex_setup`.
        """
        self._share_short_axis(sharex, 'left')  # x axis of left panels
        self._share_short_axis(sharex, 'right')
        self._share_long_axis(sharex, 'bottom')  # x axis of bottom panels
        self._share_long_axis(sharex, 'top')

    def _sharey_setup(self, sharey):
        """
        Configure y-axis sharing for panels. See also `~CartesianAxes._sharey_setup`.
        """
        self._share_short_axis(sharey, 'bottom')  # y axis of bottom panels
        self._share_short_axis(sharey, 'top')
        self._share_long_axis(sharey, 'left')  # y axis of left panels
        self._share_long_axis(sharey, 'right')

    def _share_short_axis(self, share, side):
        """
        Share the "short" axes of panels in this subplot with other panels.
        """
        if share is None or self._panel_side:
            return  # if this is a panel
        axis = 'x' if side in ('left', 'right') else 'y'
        caxs = self._panel_dict[side]
        paxs = share._panel_dict[side]
        caxs = [pax for pax in caxs if not pax._panel_hidden]
        paxs = [pax for pax in paxs if not pax._panel_hidden]
        for cax, pax in zip(caxs, paxs):  # may be uneven
            getattr(cax, '_share' + axis + '_setup')(pax)

    def _share_long_axis(self, share, side):
        """
        Share the "long" axes of panels in this subplot with other panels.
        """
        # NOTE: We do not check _panel_share because that only controls
        # sharing with main subplot, not other subplots
        if share is None or self._panel_side:
            return  # if this is a panel
        axis = 'x' if side in ('top', 'bottom') else 'y'
        paxs = self._panel_dict[side]
        paxs = [pax for pax in paxs if not pax._panel_hidden]
        for pax in paxs:
            getattr(pax, '_share' + axis + '_setup')(share)

    def _reposition_subplot(self):
        """
        Reposition the subplot axes.
        """
        # WARNING: In later versions self.numRows, self.numCols, and self.figbox
        # are @property definitions that never go stale but in mpl < 3.4 they are
        # attributes that must be updated explicitly with update_params().
        # WARNING: In early versions matplotlib only removes '_layoutbox' and
        # '_poslayoutbox' when calling public set_position but in later versions it
        # calls set_in_layout(False) which removes children from get_tightbbox().
        # Therefore try to use _set_position() even though it is private
        if not isinstance(self, maxes.SubplotBase):
            raise RuntimeError('Axes must be a subplot.')
        setter = getattr(self, '_set_position', self.set_position)
        if _version_mpl >= 3.4:
            setter(self.get_subplotspec().get_position(self.figure))
        else:
            self.update_params()
            setter(self.figbox)  # equivalent to above

    def _update_abc(self, **kwargs):
        """
        Update the a-b-c label.
        """
        # Properties
        # NOTE: Border props only apply for "inner" title locations so we need to
        # store on the axes whenever they are modified in case the current location
        # is an 'outer' location then re-apply in case 'loc' is subsequently changed
        kw = rc.fill(
            {
                'size': 'abc.size',
                'weight': 'abc.weight',
                'color': 'abc.color',
                'family': 'font.family',
            },
            context=True
        )
        kwb = rc.fill(
            {
                'border': 'abc.border',
                'borderwidth': 'abc.borderwidth',
                'bbox': 'abc.bbox',
                'bboxpad': 'abc.bboxpad',
                'bboxcolor': 'abc.bboxcolor',
                'bboxstyle': 'abc.bboxstyle',
                'bboxalpha': 'abc.bboxalpha',
            },
            context=True,
        )
        self._abc_border_kwargs.update(kwb)

        # A-b-c labels. Build as a...z...aa...zz...aaa...zzz
        abc = rc.find('abc', context=True)  # 1st run, or changed
        if abc is True:
            abc = 'a'
        if abc and (not isinstance(abc, str) or 'a' not in abc and 'A' not in abc):
            raise ValueError(f'Invalid style {abc!r}. Must include letter "a" or "A".')
        if abc and self.number is not None:
            nabc, iabc = divmod(self.number - 1, 26)
            old = re.search('[aA]', abc).group()  # return the *first* 'a' or 'A'
            new = (nabc + 1) * ABC_STRING[iabc]
            new = new.upper() if old == 'A' else new
            abc = abc.replace(old, new, 1)
            kw['text'] = abc or ''

        # Update a-b-c label
        loc = rc.find('abc.loc', context=True)
        loc = self._abc_loc = _translate_loc(loc or self._abc_loc, 'text')
        if loc not in ('left', 'right', 'center'):
            kw.update(self._abc_border_kwargs)
        kw.update(kwargs)
        self._title_dict['abc'].update(kw)
        self._above_title()

    def _update_title(self, loc, title=None, **kwargs):
        """
        Update the title at the specified location.
        """
        # Titles, with two workflows here:
        # 1. title='name' and titleloc='position'
        # 2. ltitle='name', rtitle='name', etc., arbitrarily many titles
        # NOTE: Matplotlib added axes.titlecolor in version 3.2 but we still use
        # custom title.size, title.weight, title.color properties for retroactive
        # support in older matplotlib versions. First get params and update kwargs.
        kw = rc.fill(
            {
                'size': 'title.size',
                'weight': 'title.weight',
                'color': 'title.color',
                'family': 'font.family',
            },
            context=True
        )
        if 'color' in kw and kw['color'] == 'auto':
            del kw['color']  # WARNING: matplotlib permits invalid color here
        kwb = rc.fill(
            {
                'border': 'title.border',
                'borderwidth': 'title.borderwidth',
                'bbox': 'title.bbox',
                'bboxpad': 'title.bboxpad',
                'bboxcolor': 'title.bboxcolor',
                'bboxstyle': 'title.bboxstyle',
                'bboxalpha': 'title.bboxalpha',
            },
            context=True,
        )
        self._title_border_kwargs.update(kwb)

        # Update the padding settings read at drawtime. Make sure to
        # update them on the panel axes if 'title.above' is active.
        pad = rc.find('abc.titlepad', context=True)
        if pad is not None:
            self._abc_title_pad = pad
        pad = rc.find('title.pad', context=True)  # title
        if pad is not None:
            self._title_pad = pad
            self._set_title_offset_trans(pad)

        # Get the title location. If 'titleloc' was used then transfer text
        # from the old location to the new location.
        if loc is not None:
            loc = _translate_loc(loc, 'text')
        else:
            old = self._title_loc
            loc = rc.find('title.loc', context=True)
            loc = self._title_loc = _translate_loc(loc or self._title_loc, 'text')
            if loc != old and old is not None:
                self._transfer_text(self._title_dict[old], self._title_dict[loc])

        # Update the title text. For outer panels, add text to the panel if
        # necesssary. For inner panels, use the border and bbox settings.
        if loc not in ('left', 'right', 'center'):
            kw.update(self._title_border_kwargs)
        if title is not None:
            kw['text'] = title
        kw.update(kwargs)
        self._title_dict[loc].update(kw)
        self._above_title()

    def _update_title_position(self, renderer):
        """
        Update the position of inset titles and outer titles. This is called
        by matplotlib at drawtime.
        """
        # Update title positions
        # NOTE: Critical to do this every time in case padding changes or
        # we added or removed an a-b-c label in the same position as a title
        width, height = self._get_size_inches()
        x_pad = self._title_pad / (72 * width)
        y_pad = self._title_pad / (72 * height)
        for loc, obj in self._title_dict.items():
            x, y = (0, 1)
            if loc == 'abc':  # redirect
                loc = self._abc_loc
            if loc == 'left':
                x = 0
            elif loc == 'center':
                x = 0.5
            elif loc == 'right':
                x = 1
            if loc in ('upper center', 'lower center'):
                x = 0.5
            elif loc in ('upper left', 'lower left'):
                x = x_pad
            elif loc in ('upper right', 'lower right'):
                x = 1 - x_pad
            if loc in ('upper left', 'upper right', 'upper center'):
                y = 1 - y_pad
            elif loc in ('lower left', 'lower right', 'lower center'):
                y = y_pad
            obj.set_position((x, y))

        # Push title above tick marks, since builtin algorithm seems to ignore them.
        # This is known matplotlib problem but especially annoying with top panels.
        # NOTE: See axis.get_ticks_position for inspiration
        pad = self._title_pad
        if self.xaxis.get_visible() and any(
            tick.tick2line.get_visible() and not tick.label2.get_visible()
            for tick in self.xaxis.majorTicks
        ):
            pad += self.xaxis.get_tick_padding()

        # Avoid applying padding on every draw in case it is expensive to change
        # the title Text transforms every time.
        pad_current = self._title_pad_current
        if pad_current is None or not np.isclose(pad, pad_current):
            self._title_pad_current = pad
            self._set_title_offset_trans(pad)

        # Adjust the above-axes positions with builtin algorithm
        # WARNING: Make sure the name of this private function doesn't change
        super()._update_title_position(renderer)

        # Sync the title position with the a-b-c label position
        aobj = self._title_dict['abc']
        tobj = self._title_dict[self._abc_loc]
        aobj.set_transform(tobj.get_transform())
        aobj.set_position(tobj.get_position())
        aobj.set_ha(tobj.get_ha())
        aobj.set_va(tobj.get_va())

        # Offset title away from a-b-c label
        # NOTE: Title texts all use axes transform in x-direction
        if not tobj.get_text() or not aobj.get_text():
            return
        awidth, twidth = (
            obj.get_window_extent(renderer).transformed(self.transAxes.inverted())
            .width for obj in (aobj, tobj)
        )
        ha = aobj.get_ha()
        pad = (self._abc_title_pad / 72) / self._get_size_inches()[0]
        aoffset = toffset = 0
        if ha == 'left':
            toffset = awidth + pad
        elif ha == 'right':
            aoffset = -(twidth + pad)
        else:  # guaranteed center, there are others
            toffset = 0.5 * (awidth + pad)
            aoffset = -0.5 * (twidth + pad)
        aobj.set_x(aobj.get_position()[0] + aoffset)
        tobj.set_x(tobj.get_position()[0] + toffset)

    def _update_super_title(self, suptitle=None, **kwargs):
        """
        Update the figure super title.
        """
        # NOTE: This is actually *figure-wide* setting, but that line gets blurred
        # where we have shared axes, spanning labels, etc. May cause redundant
        # assignments if using SubplotGrid.format() but this is fast so nbd.
        if self.number is None:
            # NOTE: Kludge prevents changed *figure-wide* settings from getting
            # overwritten when user makes a new panels or insets. Funky limitation but
            # kind of makes sense to make these inaccessible from panels.
            return
        kw = rc.fill(
            {
                'size': 'suptitle.size',
                'weight': 'suptitle.weight',
                'color': 'suptitle.color',
                'family': 'font.family'
            },
            context=True,
        )
        kw.update(kwargs)
        if suptitle or kw:
            self.figure._update_super_title(suptitle, **kw)

    def _update_super_labels(self, side, labels=None, **kwargs):
        """
        Update the figure super labels.
        """
        fig = self.figure
        if self.number is None:
            return  # NOTE: see above
        kw = rc.fill(
            {
                'color': side + 'label.color',
                'rotation': side + 'label.rotation',
                'size': side + 'label.size',
                'weight': side + 'label.weight',
                'family': 'font.family'
            },
            context=True,
        )
        kw.update(kwargs)
        if labels or kw:
            fig._update_super_labels(side, labels, **kw)

    @docstring._obfuscate_signature
    @_snippet_manager
    def format(
        self, *, title=None, title_kw=None, abc_kw=None,
        ltitle=None, lefttitle=None,
        ctitle=None, centertitle=None,
        rtitle=None, righttitle=None,
        ultitle=None, upperlefttitle=None,
        uctitle=None, uppercentertitle=None,
        urtitle=None, upperrighttitle=None,
        lltitle=None, lowerlefttitle=None,
        lctitle=None, lowercentertitle=None,
        lrtitle=None, lowerrighttitle=None,
        **kwargs
    ):
        """
        Modify the axes title(s), the a-b-c label, row and column labels, and
        the figure title. Called by the `~proplot.axes.CartesianAxes`,
        `~proplot.axes.PolarAxes`, and `~proplot.axes.GeoAxes` ``format`` methods.

        Parameters
        ----------
        %(axes.format)s

        Other parameters
        ----------------
        %(figure.format)s
        %(axes.rc)s

        Important
        ---------
        The `abc`, `abcstyle`, `abcloc`, `titleloc`, `titleabove`, `titlepad`,
        `abctitlepad`, `leftlabelpad`, `toplabelpad`, `rightlabelpad`, and
        `bottomlabelpad` keywords are :ref:`configuration settings <ug_config>`.
        We explicitly document these arguments here because it is very common to change
        them. But many :ref:`other configuration settings <ug_format>` can be passed
        to ``format`` too.

        See also
        --------
        proplot.config.Configurator.context
        proplot.axes.CartesianAxes.format
        proplot.axes.PolarAxes.format
        proplot.axes.GeoAxes.format
        proplot.figure.Figure.format
        """
        skip_figure = kwargs.pop('skip_figure', False)  # internal keyword arg
        rc_kw, rc_mode, kwargs = _parse_format(**kwargs)
        params = _pop_params(kwargs, self.figure.format)

        # Initiate context block
        with rc.context(rc_kw, mode=rc_mode):
            # Behavior of titles in presence of panels
            above = rc.find('title.above', context=True)
            if above is not None:
                self._title_above = above  # used for future titles
                self._above_title()  # move past titles

            # Update a-b-c label and titles
            abc_kw = abc_kw or {}
            title_kw = title_kw or {}
            self._update_abc(**abc_kw)
            self._update_title(
                None,
                title,
                **title_kw
            )
            self._update_title(
                'left',
                _not_none(ltitle=ltitle, lefttitle=lefttitle),
                **title_kw,
            )
            self._update_title(
                'center',
                _not_none(ctitle=ctitle, centertitle=centertitle),
                **title_kw,
            )
            self._update_title(
                'right',
                _not_none(rtitle=rtitle, righttitle=righttitle),
                **title_kw,
            )
            self._update_title(
                'upper left',
                _not_none(ultitle=ultitle, upperlefttitle=upperlefttitle),
                **title_kw,
            )
            self._update_title(
                'upper center',
                _not_none(uctitle=uctitle, uppercentertitle=uppercentertitle),
                **title_kw
            )
            self._update_title(
                'upper right',
                _not_none(urtitle=urtitle, upperrighttitle=upperrighttitle),
                **title_kw
            )
            self._update_title(
                'lower left',
                _not_none(lltitle=lltitle, lowerlefttitle=lowerlefttitle),
                **title_kw
            )
            self._update_title(
                'lower center',
                _not_none(lctitle=lctitle, lowercentertitle=lowercentertitle),
                **title_kw
            )
            self._update_title(
                'lower right',
                _not_none(lrtitle=lrtitle, lowerrighttitle=lowerrighttitle),
                **title_kw
            )

            # Update the axes style
            # NOTE: This will also raise an error if unknown args are encountered
            cycle = rc.find('axes.prop_cycle', context=True)
            if cycle is not None:
                self.set_prop_cycle(cycle)
            self._update_background(**kwargs)

        # Update super labels and super title
        # NOTE: To avoid resetting figure-wide settings when new axes are created
        # we only proceed if using the default context mode. Simliar to geo.py
        if skip_figure:  # avoid recursion
            return
        if rc_mode == 1:  # avoid resetting
            return
        self.figure.format(rc_kw=rc_kw, rc_mode=rc_mode, skip_axes=True, **params)

    def draw(self, renderer=None, *args, **kwargs):
        # Perform extra post-processing step
        # NOTE: In *principle* this step goes here. But should already be
        # complete because auto_layout() (called by figure pre-processor) has
        # to run them before aligning labels. So these are harmless no-ops.
        self._draw_guides()
        super().draw(renderer, *args, **kwargs)

    def get_tightbbox(self, renderer, *args, **kwargs):
        # Perform extra post-processing steps and cache the bounding box
        self._draw_guides()
        bbox = super().get_tightbbox(renderer, *args, **kwargs)
        self._tight_bbox = bbox
        return bbox

    @_snippet_manager
    def inset(self, *args, **kwargs):
        """
        %(axes.inset)s
        """
        return self.inset_axes(*args, **kwargs)

    @_snippet_manager
    def inset_axes(
        self, bounds, transform=None, *, proj=None, projection=None,
        zoom=None, zoom_kw=None, zorder=4, **kwargs
    ):
        """
        %(axes.inset)s
        """
        # Converting transform to figure-relative coordinates
        transform = self._get_transform(transform, 'axes')
        locator = self._make_inset_locator(bounds, transform)
        bb = locator(None, None)
        label = kwargs.pop('label', 'inset_axes')

        # Get projection, inherit from current axes by default
        proj = _not_none(proj=proj, projection=projection)
        if proj is None:
            proj = self.name  # will have 'proplot_' prefix
            if proj in ('proplot_cartopy', 'proplot_basemap'):
                proj = copy.copy(self.projection)
        kwargs = self.figure._parse_proj(proj, **kwargs)
        cls = mprojections.get_projection_class(kwargs.pop('projection'))

        # Create axes and apply locator. The locator lets the axes adjust
        # automatically if we used data coords. Gets called by ax.apply_aspect()
        ax = cls(self.figure, bb.bounds, zorder=zorder, label=label, **kwargs)
        ax.set_axes_locator(locator)
        ax._inset_parent = self
        self.add_child_axes(ax)

        # Add zoom indicator (NOTE: requires version >=3.0)
        zoom = _not_none(zoom, self.name == ax.name)  # only zoom when same projection
        ax._inset_zoom = zoom
        if zoom:
            zoom_kw = zoom_kw or {}
            ax.indicate_inset_zoom(**zoom_kw)
        return ax

    def indicate_inset_zoom(self, **kwargs):
        """
        Draw lines indicating the zoom range of the inset axes. This is similar
        to the builtin `~matplotlib.axes.Axes.indicate_inset_zoom` except
        lines are *refreshed* at draw-time. This is also called automatically
        when ``zoom=True`` is passed to `~Axes.inset_axes`.

        Parameters
        ----------
        alpha : float, optional
            The transparency of the zoom box fill.
        lw, linewidth : float, optional
            The width of the zoom lines and box outline in points.
        ls, linestyle : linestyle-spec, optional
            The line style for the zoom lines and box outline.
        ec, edgecolor : color-spec, optional
            The color of the zoom lines and box outline.
        capstyle : {'butt', 'round', 'projecting'}
            The cap style for the zoom lines and box outline.
        zorder : float, optional
            The `zorder <https://matplotlib.org/stable/gallery/misc/zorder_demo.html>`__
            of the zoom lines. Should be greater than the zorder of
            elements in the parent axes. Default is ``3.5``.

        Other parameters
        ----------------
        **kwargs
            Passed to `~matplotlib.axes.Axes.indicate_inset`.
        """
        # Should be called from the inset axes
        parent = self._inset_parent
        props = _pop_props(kwargs, 'patch')
        props.setdefault('zorder', 3.5)
        props.setdefault('linewidth', rc['axes.linewidth'])
        props.setdefault('edgecolor', rc['axes.edgecolor'])
        kwargs.setdefault('capstyle', 'round')  # match zoom capstyle
        if not parent:
            raise ValueError(f'{self} is not an inset axes.')
        xlim, ylim = self.get_xlim(), self.get_ylim()
        rect = (xlim[0], ylim[0], xlim[1] - xlim[0], ylim[1] - ylim[0])

        # Call indicate_inset
        rectpatch, connects = parent.indicate_inset(
            rect, self, **props, **kwargs
        )

        # Update zoom or adopt properties from old one
        if self._inset_zoom_data is None:
            for line in connects:
                line.update(props)
        else:
            rectpatch_prev, connects_prev = self._inset_zoom_data
            rectpatch.update_from(rectpatch_prev)
            rectpatch_prev.set_visible(False)
            for line, line_prev in zip(connects, connects_prev):
                visible = line.get_visible()
                line.update_from(line_prev)
                line.set_visible(visible)
                line_prev.set_visible(False)
        self._inset_zoom_data = (rectpatch, connects)
        return rectpatch, connects

    @_snippet_manager
    def panel(self, *args, **kwargs):
        """
        %(axes.panel)s
        """
        return self.panel_axes(*args, **kwargs)

    @_snippet_manager
    def panel_axes(self, *args, **kwargs):
        """
        %(axes.panel)s
        """
        self = self._altx_parent or self
        self = self._alty_parent or self
        if not isinstance(self, maxes.SubplotBase):
            raise RuntimeError('Cannot create panels for non-subplot axes.')
        if self._panel_parent:
            raise RuntimeError('Cannot create panels for existing panel axes.')
        return self.figure._add_axes_panel(self, *args, **kwargs)

    def _above_title(self):
        """
        Change assignment of outer titles between main subplot and upper panels.
        This is called when a panel is created or `_update_title` is called.
        """
        # NOTE: After the panel is created, calling format() will automatically
        # reassign titles, a-b-c labels, and super labels
        paxs = self._panel_dict['top']
        if not paxs:
            return
        pax = paxs[-1]
        names = ('left', 'center', 'right')
        if self._abc_loc in names:
            names += ('abc',)
        if self._title_above is True or not pax._panel_hidden and self._title_above == 'panels':  # noqa: E501
            src, dest = self, pax
        else:
            src, dest = pax, self
        for name in names:
            self._transfer_text(src._title_dict[name], dest._title_dict[name])
        dest._title_pad = src._title_pad
        dest._abc_title_pad = src._abc_title_pad

    def _auto_share(self):
        """
        Automatically configure axis sharing based on the horizontal and
        vertical extent of subplots in the figure gridspec.
        """
        # Panel axes sharing, between main subplot and its panels
        # NOTE: _panel_share means "include this panel in the axis sharing group"
        # while _panel_sharex_group indicates the group itself and may include main axes
        def shared(paxs):
            return [pax for pax in paxs if not pax._panel_hidden and pax._panel_share]

        # Internal axis sharing, share stacks of panels and main axes with each other
        # NOTE: This is called on the main axes whenver a panel is created.
        # NOTE: This block is why, even though we have figure-wide share[xy], we
        # still need the axes-specific _share[xy]_override attribute.
        if not self._panel_side:  # this is a main axes
            # Top and bottom
            bottom = self
            paxs = shared(self._panel_dict['bottom'])
            if paxs:
                bottom = paxs[-1]
                bottom._panel_sharex_group = False
                for iax in (self, *paxs[:-1]):
                    iax._panel_sharex_group = True
                    iax._sharex_setup(bottom)  # parent is bottom-most
            paxs = shared(self._panel_dict['top'])
            for iax in paxs:
                iax._panel_sharex_group = True
                iax._sharex_setup(bottom)
            # Left and right
            # NOTE: Order of panel lists is always inside-to-outside
            left = self
            paxs = shared(self._panel_dict['left'])
            if paxs:
                left = paxs[-1]
                left._panel_sharey_group = False
                for iax in (self, *paxs[:-1]):
                    iax._panel_sharey_group = True
                    iax._sharey_setup(left)  # parent is left-most
            paxs = shared(self._panel_dict['right'])
            for iax in paxs:
                iax._panel_sharey_group = True
                iax._sharey_setup(left)

        # External axes sharing, sometimes overrides panel axes sharing
        # NOTE: This can get very repetitive, but probably minimal impact?
        # Share x axes
        parent, *children = self._get_share_axes('x')
        for child in children:
            child._sharex_setup(parent)
        # Share y axes
        parent, *children = self._get_share_axes('y')
        for child in children:
            child._sharey_setup(parent)

    def _add_guide(self, guide, obj, loc, **kwargs):
        """
        Queue up or replace objects for legends and list-of-artist style colorbars.
        """
        # Initial stuff
        if guide not in ('legend', 'colorbar'):
            raise TypeError(f'Invalid type {guide!r}.')
        dict_ = self._legend_dict if guide == 'legend' else self._colorbar_dict
        if loc == 'fill':
            loc = self._panel_side
            if loc is None:  # cannot register 'filled' non panels
                return

        # Remove previous instances
        # NOTE: No good way to remove inset colorbars right now until the bounding
        # box and axes are merged into some kind of subclass. Just fine for now.
        if loc in dict_ and not isinstance(dict_[loc], tuple):
            obj_prev = dict_.pop(loc)  # possibly pop a queued object
            if guide == 'colorbar':
                pass
            elif hasattr(self, 'legend_') and self.legend_ is obj_prev:
                self.legend_ = None  # was never added as artist
            else:
                obj_prev.remove()  # remove legends and inner colorbars

        # Replace with instance or update the queue
        # NOTE: This replaces previous legends
        if isinstance(obj, tuple) and not any(isinstance(_, mlegend.Legend) for _ in obj):  # noqa: E501
            handles, labels = obj
            handles = _not_none(handles, [])
            if not isinstance(handles, list):
                handles = [handles]  # e.g. mappable
            labels = _not_none(labels, [])
            if not isinstance(labels, list):
                labels = [labels]  # not sure if this ever happens
            handles_full, labels_full, kwargs_full = dict_.setdefault(loc, ([], [], {}))
            handles_full.extend(_not_none(handles, []))
            labels_full.extend(_not_none(labels, []))
            kwargs_full.update(kwargs)
        else:
            dict_[loc] = obj

    def _draw_guides(self):
        """
        Draw the queued-up legends and colorbars. Wrapper funcs and legend func let
        user add handles to location lists with successive calls.
        """
        # Draw queued colorbars
        for loc, colorbar in tuple(self._colorbar_dict.items()):
            if not isinstance(colorbar, tuple):
                continue
            handles, labels, kwargs = colorbar
            cb = self._draw_colorbar(handles, labels or None, loc=loc, **kwargs)
            self._colorbar_dict[loc] = cb

        # Draw queued legends
        # WARNING: Passing empty list labels=[] to legend causes matplotlib
        # _parse_legend_args to search for everything. Ensure None if empty.
        for loc, legend in tuple(self._legend_dict.items()):
            if not isinstance(legend, tuple) or any(isinstance(_, mlegend.Legend) for _ in legend):  # noqa: E501
                continue
            handles, labels, kwargs = legend
            leg = self._draw_legend(handles, labels or None, loc=loc, **kwargs)
            self._legend_dict[loc] = leg

    def _fill_colorbar_axes(
        self, length=None, shrink=None,
        tickloc=None, ticklocation=None, orientation=None, **kwargs
    ):
        """
        Return the axes and adjusted keyword args for a panel-filling colorbar.
        """
        side = self._panel_side
        length = _not_none(length=length, shrink=shrink, default=rc['colorbar.length'])
        ticklocation = _not_none(tickloc=tickloc, ticklocation=ticklocation)
        if not 0 < length <= 1:
            raise ValueError('Panel colorbar length must satisfy 0 < length <= 1.')
        if not isinstance(self, maxes.SubplotBase):
            raise RuntimeError('Axes must be a subplot.')

        # Draw colorbar axes within this one
        # WARNING: Use internal keyword arg '_child'
        ss = self.get_subplotspec()
        ratios = (0.5 * (1 - length), length, 0.5 * (1 - length))
        if side in ('bottom', 'top'):
            nrows, ncols = (1, 3)
            hratios, wratios = (1,), ratios
        else:
            nrows, ncols = (3, 1)
            hratios, wratios = ratios, (1,)
        gs = mgridspec.GridSpecFromSubplotSpec(
            nrows, ncols, ss,
            hspace=0, wspace=0, height_ratios=hratios, width_ratios=wratios,
        )
        ss = pgridspec._SubplotSpec(gs, 1, 1)
        self._hide_panel()
        ax = self.figure.add_subplot(ss, autoshare=False, number=False)
        ax.patch.set_facecolor('none')  # ignore axes.alpha application
        self.add_child_axes(ax)

        # Handle default keyword args
        side = _not_none(side, 'left' if orientation == 'vertical' else 'bottom')
        if side in ('bottom', 'top'):
            outside, inside = 'bottom', 'top'
            if side == 'top':
                outside, inside = inside, outside
            ticklocation = _not_none(ticklocation, outside)
            orientation = _not_none(orientation, 'horizontal')
        else:
            outside, inside = 'left', 'right'
            if side == 'right':
                outside, inside = inside, outside
            ticklocation = _not_none(ticklocation, outside)
            orientation = _not_none(orientation, 'vertical')
        kwargs.update({
            'orientation': orientation,
            'ticklocation': ticklocation
        })

        return ax, kwargs

    def _inset_colorbar_axes(
        self, loc=None, width=None, length=None, shrink=None,
        frame=None, frameon=None, label=None, pad=None,
        tickloc=None, ticklocation=None, orientation=None,
        **kwargs,
    ):
        """
        Return the axes and adjusted keyword args for an inset colorbar.
        """
        # Frame properties
        # NOTE: Compare to same block in legend() code.
        kw_patch = _pop_kwargs(
            kwargs,
            alpha=('a', 'framealpha', 'facealpha'),
            facecolor=('fc', 'framecolor'),
            edgecolor=('ec',),
            linewidth=('lw',),
        )
        kw_patch['zorder'] = 4
        kw_patch.setdefault('alpha', rc['colorbar.framealpha'])
        kw_patch.setdefault('edgecolor', rc['colorbar.edgecolor'])
        kw_patch.setdefault('facecolor', rc['colorbar.facecolor'])
        kw_patch.setdefault('linewidth', rc['axes.linewidth'])

        # Basic colorbar properties
        frame = _not_none(frame=frame, frameon=frameon, default=rc['colorbar.frameon'])
        length = _not_none(length=length, shrink=shrink, default=rc['colorbar.insetlength'])  # noqa: E501
        width = _not_none(width, rc['colorbar.insetwidth'])
        pad = _not_none(pad, rc['colorbar.insetpad'])
        length = units(length, 'em', 'ax', axes=self, width=True)  # x direction
        width = units(width, 'em', 'ax', axes=self, width=False)  # y direction
        xpad = units(pad, 'em', 'ax', axes=self, width=True)
        ypad = units(pad, 'em', 'ax', axes=self, width=False)

        # Extra space accounting for colorbar label and tick labels
        labspace = rc['xtick.major.size'] / 72
        if label is not None:
            labspace += 2.4 * rc['font.size'] / 72
        else:
            labspace += 1.2 * rc['font.size'] / 72
        labspace /= self._get_size_inches()[1]  # space for labels

        # Location in axes-relative coordinates
        # Bounds are x0, y0, width, height in axes-relative coordinates
        if loc == 'upper right':
            ibounds = (1 - xpad - length, 1 - ypad - width)
            fbounds = (1 - 2 * xpad - length, 1 - 2 * ypad - width - labspace)
        elif loc == 'upper left':
            ibounds = (xpad, 1 - ypad - width)
            fbounds = (0, 1 - 2 * ypad - width - labspace)
        elif loc == 'lower left':
            ibounds = (xpad, ypad + labspace)
            fbounds = (0, 0)
        else:
            ibounds = (1 - xpad - length, ypad + labspace)
            fbounds = (1 - 2 * xpad - length, 0)
        ibounds = (*ibounds, length, width)  # inset axes
        fbounds = (*fbounds, 2 * xpad + length, 2 * ypad + width + labspace)

        # Make frame
        # NOTE: We do not allow shadow effects or fancy edges effect.
        # Also keep zorder same as with legend.
        if frame:
            xmin, ymin, width, height = fbounds
            patch = mpatches.Rectangle(
                (xmin, ymin), width, height, snap=True, transform=self.transAxes
            )
            patch.update(kw_patch)
            self.add_artist(patch)

        # Make axes
        from .cartesian import CartesianAxes
        locator = self._make_inset_locator(ibounds, self.transAxes)
        bbox = locator(None, None)
        ax = CartesianAxes(self.figure, bbox.bounds, zorder=5)
        ax.set_axes_locator(locator)
        self.add_child_axes(ax)

        # Default keyword args
        if orientation is not None and orientation != 'horizontal':
            warnings._warn_proplot(
                f'Orientation for inset colorbars must be horizontal, '
                f'ignoring orientation={orientation!r}.'
            )
        ticklocation = _not_none(tickloc=tickloc, ticklocation=ticklocation)
        if ticklocation is not None and ticklocation != 'bottom':
            warnings._warn_proplot('Inset colorbars can only have ticks on the bottom.')
        kwargs.update({
            'orientation': 'horizontal',
            'ticklocation': 'bottom',
        })
        kwargs.setdefault('maxn', 5)  # passed to _parse_colorbar_ticks
        return ax, kwargs

    def _parse_colorbar_ticks(
        self, mappable, ticks=None, locator=None, locator_kw=None,
        format=None, formatter=None, ticklabels=None, formatter_kw=None,
        minorticks=None, minorlocator=None, minorlocator_kw=None,
        maxn=None, maxn_minor=None, tickminor=None, fontsize=None, **kwargs,
    ):
        """
        Get the default locator for colorbar ticks.
        """
        ticks = _not_none(ticks=ticks, locator=locator)
        formatter = _not_none(ticklabels=ticklabels, formatter=formatter, format=format)
        minorlocator = _not_none(minorticks=minorticks, minorlocator=minorlocator)
        locator_kw = locator_kw or {}
        formatter_kw = formatter_kw or {}
        minorlocator_kw = minorlocator_kw or {}

        # Get ticks at level locations
        # NOTE: We virtually always want to subsample the level list. For example
        # for LogNorm _parse_autolev will interpolate to even points in log-space
        # between powers of 10 if the powers don't give us enough levels. Therefore
        # x/y axis-style unevenly spaced log minor ticks would be confusing/ugly.
        def _subsample_levels(maxn, scale, size):
            maxn = _not_none(maxn, int(length / (scale * size / 72)))
            diff = abs(ticks[1] - ticks[0])
            step = 1 + len(ticks) // max(1, maxn)
            idx, = np.where(np.isclose(np.array(ticks) % (step * diff), 0.0))
            if idx.size:
                locs = ticks[idx[0] % step::step]  # even multiples from zero
            else:
                locs = ticks[::step]  # unknown offset
            return locs

        # Get colorbar locator
        # NOTE: Do not necessarily want minor tick locations at logminor for LogNorm!
        # In _auto_discrete_norm we sometimes select evenly spaced levels in log-space
        # *between* powers of 10, so logminor ticks would be misaligned with levels.
        if ticks is None:
            # This should only happen if discrete=False since _parse_levels supplies
            # default ticks to the colorbar. Treat this as smooth gradations.
            if isinstance(mappable.norm, mcolors.LogNorm):
                locator = 'log'
            elif isinstance(mappable.norm, mcolors.SymLogNorm):
                locator = 'symlog'
                locator_kw.setdefault('linthresh', mappable.norm.linthresh)
            else:
                locator = 'auto'
        elif np.iterable(ticks) and not isinstance(ticks, str) and len(ticks) > 1:
            # These are usually ticks passed by _parse_levels but may also be user
            # input lists. Users can use pplt.Locator(ticks) to avoid subsampling.
            width, height = self._get_size_inches()
            if kwargs.get('orientation', None) == 'vertical':
                length, scale, axis = height, 1.0, 'y'
            else:
                length, scale, axis = width, 2.5, 'x'
            size = _fontsize_to_pt(_not_none(fontsize, rc[axis + 'tick.labelsize']))
            locator = _subsample_levels(maxn, scale, size)
            if tickminor and minorlocator is None:
                minorlocator = _subsample_levels(maxn_minor, 0.5, size)
        else:
            # Manually specified locator
            locator = ticks

        # Return tickers
        locator = constructor.Locator(locator, **locator_kw)
        if tickminor and minorlocator is None:
            minorlocator = 'minor'
        if minorlocator is not None:
            minorlocator = constructor.Locator(minorlocator, **minorlocator_kw)
        formatter = _not_none(formatter, 'auto')
        formatter = constructor.Formatter(formatter, **formatter_kw)
        return locator, formatter, minorlocator, kwargs

    def _parse_mappable_values(
        self, mappable, values=None, *, norm=None, norm_kw=None, **kwargs,
    ):
        """
        Generate a mappable from flexible non-mappable input. Useful in bridging
        the gap between legends and colorbars (e.g., creating colorbars from line
        objects whose data values span a natural colormap range).
        """
        # Special case where auto colorbar is generated from 1d methods, a list is
        # always passed, but some 1d methods (scatter) do have colormaps.
        if (
            np.iterable(mappable)
            and len(mappable) == 1
            and isinstance(mappable[0], mcm.ScalarMappable)
        ):
            mappable = mappable[0]
        if isinstance(mappable, mcm.ScalarMappable):
            return mappable, kwargs
        else:
            locator = _not_none(kwargs.pop('locator', None), kwargs.pop('ticks', None))
            formatter = _not_none(kwargs.pop('ticklabels', None), kwargs.pop('formatter', None))  # noqa: E501
            rotation = kwargs.pop('rotation', None)

        # For container objects, we just assume color is the same for every item.
        # Works for ErrorbarContainer, StemContainer, BarContainer.
        if (
            np.iterable(mappable)
            and len(mappable) > 0
            and all(isinstance(obj, mcontainer.Container) for obj in mappable)
        ):
            mappable = [obj[0] for obj in mappable]

        # A colormap instance
        if isinstance(mappable, mcolors.Colormap) or isinstance(mappable, str):
            # NOTE: 'Values' makes no sense if this is just a colormap. Just
            # use unique color for every segmentdata / colors color.
            cmap = constructor.Colormap(mappable)
            values = np.linspace(0, 1, cmap.N)

        # List of colors
        elif np.iterable(mappable) and all(
            isinstance(obj, str) or (np.iterable(obj) and len(obj) in (3, 4))
            for obj in mappable
        ):
            cmap = pcolors.DiscreteColormap(list(mappable), '_no_name')
            if values is None:
                values = np.arange(len(mappable))
            locator = _not_none(locator, values)  # tick all values by default

        # List of artists
        # NOTE: Do not check for isinstance(Artist) in case it is an mpl collection
        elif np.iterable(mappable) and all(
            hasattr(obj, 'get_color') or hasattr(obj, 'get_facecolor')
            for obj in mappable
        ):
            # Generate colormap from colors and infer tick labels
            colors = []
            for obj in mappable:
                if hasattr(obj, 'get_color'):
                    color = obj.get_color()
                else:
                    color = obj.get_facecolor()
                if isinstance(color, np.ndarray):
                    color = color.squeeze()  # e.g. scatter plot
                    if color.ndim != 1:
                        raise ValueError(
                            'Cannot make colorbar from list of artists '
                            f'with more than one color: {color!r}.'
                        )
                colors.append(to_rgb(color))

            # Try to infer tick values and tick labels from Artist labels
            cmap = pcolors.DiscreteColormap(colors, '_no_name')
            if values is None:
                # Get object labels and values
                labels = []
                values = []
                for obj in mappable:
                    label = obj.get_label()  # could be None
                    if isinstance(label, str) and label[:1] == '_':
                        label = None
                    try:
                        value = float(label)  # could be float(None)
                    except (TypeError, ValueError):
                        value = None
                    labels.append(label)
                    values.append(value)
                # Use default values if labels are non-numeric (numeric labels are
                # common when making on-the-fly colorbars). Try to use object labels
                # for ticks with default vertical rotation, like datetime axes.
                if any(value is None for value in values):
                    values = np.arange(len(mappable))
                    if any(_ is not None for _ in labels):
                        formatter = _not_none(formatter, labels)
                        if kwargs.get('orientation', None) != 'vertical':
                            rotation = _not_none(rotation, 90)
            # Tick all values by default
            locator = _not_none(locator, values)

        else:
            raise ValueError(
                'Input mappable must be a matplotlib artist, '
                'list of objects, list of colors, or colormap. '
                f'Got {mappable!r}.'
            )

        # Build ad hoc ScalarMappable object from colors
        if np.iterable(mappable) and len(values) != len(mappable):
            raise ValueError(
                f'Passed {len(values)} values, but only {len(mappable)} '
                f'objects or colors.'
            )
        norm_kw = norm_kw or {}
        norm = constructor.Norm(norm or 'linear', **norm_kw)
        if len(values) > 1:
            levels = edges(values)
        elif len(values) == 1:
            levels = [values[0] - 1, values[0] + 1]
        norm, cmap, _ = self._parse_discrete(levels, norm, cmap)
        mappable = mcm.ScalarMappable(norm, cmap)

        kwargs.update({'locator': locator, 'formatter': formatter, 'rotation': rotation})  # noqa: E501
        return mappable, kwargs

    def _draw_colorbar(
        self, mappable, values=None, *, loc=None, space=None, pad=None,
        extend=None, reverse=False, tickdir=None, tickdirection=None, tickminor=None,
        title=None, label=None, norm=None, norm_kw=None,
        ec=None, edgecolor=None, lw=None, linewidth=None, edgefix=None,
        labelsize=None, labelweight=None, labelcolor=None,
        ticklabelsize=None, ticklabelweight=None, ticklabelcolor=None,
        grid=None, edges=None, drawedges=None, rasterize=None,
        extendsize=None, extendfrac=None, **kwargs
    ):
        """
        The driver function for adding axes colorbars.
        """
        # Parse input axes
        # TODO: Get the 'best' inset colorbar location using the legend algorithm.
        # NOTE: There is a weird problem with colorbars when simultaneously
        # passing levels and norm object to a mappable; fixed by passing vmin/vmax
        # instead of levels. (see: https://stackoverflow.com/q/40116968/4970632).
        # NOTE: Often want levels instead of vmin/vmax, while simultaneously
        # using a Normalize (for example) to determine colors between the levels
        # (see: https://stackoverflow.com/q/42723538/4970632). Workaround makes
        # sure locators are in vmin/vmax range exclusively; cannot match values.
        norm_kw = norm_kw or {}
        grid = _not_none(grid=grid, edges=edges, drawedges=drawedges, default=rc['colorbar.grid'])  # noqa: E501
        label = _not_none(title=title, label=label)
        linewidth = _not_none(lw=lw, linewidth=linewidth, default=rc['axes.linewidth'])
        edgecolor = _not_none(ec=ec, edgecolor=edgecolor, default=rc['colorbar.edgecolor'])  # noqa: E501
        tickdir = _not_none(tickdir=tickdir, tickdirection=tickdirection)
        rasterize = _not_none(rasterize, rc['colorbar.rasterize'])

        # Generate an axes panel
        # NOTE: The inset axes function needs 'label' to know how to pad the box
        # TODO: Use seperate keywords for frame properties vs. colorbar edge properties?
        if loc in ('left', 'right', 'top', 'bottom'):
            width = kwargs.pop('width', None)
            self = self.panel_axes(loc, width=width, space=space, pad=pad, filled=True)
            loc = 'fill'
        if loc == 'fill':
            kwargs.pop('width', None)
            extendsize = _not_none(extendsize, rc['colorbar.extend'])
            cax, kwargs = self._fill_colorbar_axes(**kwargs)
        else:
            kwargs.update({'linewidth': linewidth, 'edgecolor': edgecolor, 'label': label})  # noqa: E501
            extendsize = _not_none(extendsize, rc['colorbar.insetextend'])
            cax, kwargs = self._inset_colorbar_axes(loc=loc, pad=pad, **kwargs)  # noqa: E501

        # Parse the mappable and get the locator or formatter. Try to get them from
        # values or artist labels rather than random points if possible.
        # WARNING: Matplotlib >= 3.4 seems to have issue with assigning no ticks
        # to colorbar. Tried to fix with below block but doesn't seem to help.
        mappable, kwargs = cax._parse_mappable_values(
            mappable, values, **kwargs
        )
        locator, formatter, minorlocator, kwargs = cax._parse_colorbar_ticks(
            mappable, fontsize=ticklabelsize, tickminor=tickminor, **kwargs,
        )
        if isinstance(locator, mticker.NullLocator):
            locator = []  # passed as 'ticks'
        if isinstance(minorlocator, mticker.NullLocator):
            minorlocator, tickminor = None, False

        # Parse text property keyword args
        kw_label = {}
        for key, value in (
            ('size', labelsize),
            ('weight', labelweight),
            ('color', labelcolor),
        ):
            if value is not None:
                kw_label[key] = value
        kw_ticklabels = {}
        for key, value in (
            ('size', ticklabelsize),
            ('weight', ticklabelweight),
            ('color', ticklabelcolor),
            ('rotation', kwargs.pop('rotation', None)),
        ):
            if value is not None:
                kw_ticklabels[key] = value

        # Parse extend triangle keyword args
        if extendsize is not None and extendfrac is not None:
            warnings._warn_proplot(
                f'You cannot specify both an absolute extendsize={extendsize!r} '
                f"and a relative extendfrac={extendfrac!r}. Ignoring 'extendfrac'."
            )
            extendfrac = None
        if extendfrac is None:
            orientation = kwargs.get('orientation', 'horizontal')  # should be there
            width, height = cax._get_size_inches()
            scale = height if orientation == 'vertical' else width
            extendsize = units(extendsize, 'em', 'in')
            extendfrac = extendsize / max(scale - 2 * extendsize, units(1, 'em', 'in'))

        # Draw the colorbar
        # NOTE: Set default formatter here because we optionally apply a FixedFormatter
        # using *labels* from handle input.
        kwargs.update({
            'cax': cax,
            'ticks': locator,
            'format': formatter,
            'extendfrac': extendfrac,
            'drawedges': grid,
        })
        kwargs.setdefault('spacing', 'uniform')
        extend = _not_none(extend, 'neither')
        if isinstance(mappable, mcontour.ContourSet):
            mappable.extend = extend  # required in mpl >= 3.3, else optional
        else:
            kwargs['extend'] = extend
        obj = self.figure.colorbar(mappable, **kwargs)

        # Label and tick label settings
        # WARNING: Must use colorbar set_label to set text, calling set_text on
        # the axis will do nothing!
        axis = cax.yaxis if orientation == 'vertical' else cax.xaxis
        if label is not None:
            obj.set_label(label)
        axis.label.update(kw_label)
        for label in axis.get_ticklabels():
            label.update(kw_ticklabels)
        axis.set_tick_params(
            which='both', color=edgecolor, width=linewidth, direction=tickdir
        )

        # The minor locator
        # NOTE: Colorbar._use_auto_colorbar_locator() is never True because we use
        # the custom DiscreteNorm normalizer. Colorbar._ticks() always called.
        if minorlocator is None:
            if tickminor:
                obj.minorticks_on()
            else:
                obj.minorticks_off()
        elif not hasattr(obj, '_ticker'):
            warnings._warn_proplot(
                'Matplotlib colorbar API has changed. Cannot use '
                f'custom minor tick locator {minorlocator!r}.'
            )
            obj.minorticks_on()  # at least turn them on
        else:
            # Set the minor ticks just like matplotlib internally sets the
            # major ticks. Private API is the only way!
            minorlocator.set_axis(axis)
            ticks, *_ = obj._ticker(minorlocator, mticker.NullFormatter())
            axis.set_ticks(ticks, minor=True)
            axis.set_ticklabels([], minor=True)

        # Fix alpha-blending issues. Cannot set edgecolor to 'face' because blending
        # will occur, get colored lines instead of white ones. Need manual blending.
        # NOTE: For some reason cb solids uses listed colormap with always 1.0 alpha,
        # then alpha is applied after. See: https://stackoverflow.com/a/35672224/4970632
        cmap = obj.cmap
        blend = rc.get('pcolormesh.snap', False)  # rely on this only if available
        if not cmap._isinit:
            cmap._init()
        if blend and any(cmap._lut[:-1, 3] < 1):
            warnings._warn_proplot(
                f'Using manual alpha-blending for {cmap.name!r} colorbar solids.'
            )
            lut = cmap._lut.copy()
            cmap = mcolors.Colormap('_no_name', N=cmap.N)
            cmap._isinit = True
            cmap._init = lambda: None
            for i in range(lut.shape[0] - 1):
                alpha = lut[i, 3]
                lut[i, :3] = (1 - alpha) * 1 + alpha * lut[i, :3]  # blend *white*
                lut[i, 3] = 1  # set to opaque
            cmap._lut = lut
            obj.cmap = cmap
            obj.draw_all()  # update contents

        # Fix colorbar outline
        kw_outline = {'edgecolor': edgecolor, 'linewidth': linewidth}
        if obj.outline is not None:
            obj.outline.update(kw_outline)
        if obj.dividers is not None:
            obj.dividers.update(kw_outline)

        # Disable rasterization by default because it causes misalignment with grid
        if obj.solids:
            cax._fix_edges(obj.solids, edgefix=edgefix)
            obj.solids.set_rasterized(rasterize)

        # Invert the axis if norm is a descending DiscreteNorm
        norm = mappable.norm
        if getattr(norm, 'descending', None):
            axis.set_inverted(True)
        if reverse:  # potentially double reverse, although that would be weird...
            axis.set_inverted(True)

        # Return after registering location
        self._add_guide('colorbar', obj, loc)  # possibly replace another
        return obj

    @docstring._obfuscate_signature
    @_snippet_manager
    def colorbar(
        self, mappable, values=None, *, loc=None, location=None, queue=False,
        **kwargs
    ):
        """
        Add an inset colorbar or an outer colorbar along the edge of the axes.

        Parameters
        ----------
        %(axes.colorbar_args)s
        loc, location : str, optional
            The colorbar location. Default is :rc:`colorbar.loc`. Valid location
            keys are shown in the below table.

            .. _colorbar_table:

            ==================  =======================================
            Location            Valid keys
            ==================  =======================================
            outer left          ``'left'``, ``'l'``
            outer right         ``'right'``, ``'r'``
            outer bottom        ``'bottom'``, ``'b'``
            outer top           ``'top'``, ``'t'``
            default inset       ``'best'``, ``'inset'``, ``'i'``, ``0``
            upper right inset   ``'upper right'``, ``'ur'``, ``1``
            upper left inset    ``'upper left'``, ``'ul'``, ``2``
            lower left inset    ``'lower left'``, ``'ll'``, ``3``
            lower right inset   ``'lower right'``, ``'lr'``, ``4``
            "filled"            ``'fill'``
            ==================  =======================================

        length : float or str, optional
            The colorbar length. For outer colorbars, default is :rc:`colorbar.length`
            and units are relative to the axes width or height. For inset default is
            :rc:`colorbar.insetlength`. %(units.em)s
        shrink : float, optional
            Alias for `length`. This is included for consistency with
            `matplotlib.figure.Figure.colorbar`.
        width : float or str, optional
            The colorbar width. If string, units are interpreted by
            `~proplot.utils.units`. For outer colorbars, default is
            :rc:`colorbar.width`, and if float, units are inches.
            For inset colorbars, default is :rc:`colorbar.insetwidth`,
            and if float, units are font size-relative.
        %(axes.colorbar_space)s

        Other parameters
        ----------------
        %(axes.colorbar_kwargs)s

        See also
        --------
        proplot.figure.Figure.colorbar
        matplotlib.figure.Figure.colorbar
        """
        # Either draw right now or queue up for later
        # The queue option lets us successively append objects (e.g. line handles)
        # to a list later used for colorbar levels. Same as legend.
        loc = _not_none(loc=loc, location=location)
        loc = _translate_loc(loc, 'colorbar', default=rc['colorbar.loc'])
        kwargs = _guide_kw_from_obj(mappable, 'colorbar', kwargs)
        if queue:
            obj = (mappable, values)
            self._add_guide('colorbar', obj, loc, **kwargs)
        else:
            cb = self._draw_colorbar(mappable, values, loc=loc, **kwargs)
            return cb

    @staticmethod
    def _parse_handle_groups(handles, labels=None):
        """
        Parse possibly tuple-grouped input handles.
        """
        # Helper functions. Filter objects in a tuple group and retrieve
        # labels from a tuple group. Possibly return none of either.
        def _group_labs(*objs):  # noqa: E301
            labs = []
            for obj in objs:
                lab = obj.get_label()
                if lab is not None and str(lab)[:1] != '_':
                    labs.append(lab)
            return labs
        def _group_objs(*objs):  # noqa: E306
            out = []
            ignore = (mcontainer.ErrorbarContainer,)
            for obj in objs:
                if isinstance(obj, ignore) and not _group_labs(obj):
                    continue
                elif isinstance(obj, cbook.silent_list) and obj:
                    obj = obj[0]
                if hasattr(obj, 'get_label') or type(obj) is tuple:
                    out.append(obj)
            return tuple(out)

        # Sanitize labels. Ignore e.g. extra hist() or hist2d() return values,
        # auto-detect labels in tuple group, auto-expand tuples with diff labels
        # NOTE: Allow handles and labels of different length like native
        # matplotlib. Just truncate extra values with zip().
        if labels is None:
            labels = [None] * len(handles)
        ihandles, ilabels = [], []
        for objs, label in zip(handles, labels):
            # Filter objects
            # WARNING: Matplotlib Containers are tuples and silent_lists
            # are lists so we must test identities here.
            if type(objs) is list and len(objs) == 1:
                objs = objs[0]
            if type(objs) is not tuple:
                objs = (objs,)
            objs = _group_objs(*objs)
            labs = set(_group_labs(*objs))
            if not objs:
                continue
            # Unfurl tuple of handles
            if label is None and len(labs) > 1:
                ihandles.extend(objs)
                ilabels.extend(obj.get_label() for obj in objs)
            # Append this handle with some name
            else:
                if label is None:
                    label = labs.pop() if labs else '_no_label'
                ihandles.append(objs)
                ilabels.append(label)

        return ihandles, ilabels

    def _parse_handles_labels(
        self, axs, handles, labels, ncol=None, order='C', center=None, alphabetize=None,
    ):
        """
        Parse input handles and labels.
        """
        # Helper function
        # TODO: Often desirable to label a "mappable" with one data value. Maybe add a
        # legend option for the *number of samples* or *sample points* when drawing
        # legends for mappables. Look into "legend handlers", might just want to add
        # handlers by passing handler_map to legend() and get_legend_handles_labels().
        def _to_list(obj):  # noqa: E301
            if obj is None:
                pass
            elif isinstance(obj, np.ndarray):
                obj = obj.tolist()
            elif not isinstance(obj, list):
                obj = [obj]
            return obj

        # Handle lists of lists
        axs = axs or ()
        handles, labels = _to_list(handles), _to_list(labels)
        if handles is None:
            list_of_lists = False
        else:
            list_of_lists = any(
                isinstance(h, (list, np.ndarray)) and len(h) > 1 for h in handles
            )
        if list_of_lists and ncol is not None:
            warnings._warn_proplot(
                'Detected list of *lists* of legend handles. '
                'Ignoring user input property "ncol".'
            )
        if list_of_lists and order == 'F':
            raise NotImplementedError(
                'Column-major ordering of legend handles is not supported '
                'for horizontally-centered legends.'
            )
        ncol = _not_none(ncol, 3)
        center = _not_none(center, list_of_lists)

        # Iterate over each sublist and parse independently
        pairs = []
        if not list_of_lists:  # temporary
            handles, labels = [handles], [labels]
        for ihandles, ilabels in zip(handles, labels):
            ihandles, ilabels = _to_list(ihandles), _to_list(ilabels)
            if ihandles is not None:
                ihandles, ilabels = self._parse_handle_groups(ihandles, ilabels)
            ihandles, ilabels, *_ = mlegend._parse_legend_args(
                axs, handles=ihandles, labels=ilabels,
            )
            ipairs = list(zip(ihandles, ilabels))
            if alphabetize:
                ipairs = sorted(ipairs, key=lambda pair: pair[1])
            pairs.append(ipairs)

        # Manage (handle, label) pairs in context of the 'center' option
        if not list_of_lists:
            pairs = pairs[0]
            if center:
                list_of_lists = True
                pairs = [pairs[i * ncol:(i + 1) * ncol] for i in range(len(pairs))]
        else:
            if not center:  # standardize format based on input
                list_of_lists = False  # no longer is list of lists
                pairs = [pair for ipairs in pairs for pair in ipairs]
        if list_of_lists:  # remove empty sublists
            pairs = [ipairs for ipairs in pairs if ipairs]

        return pairs

    @staticmethod
    def _legend_objects(children):
        """
        Iterate recursively through `_children` attributes of various `HPacker`,
        `VPacker`, and `DrawingArea` classes.
        """
        for obj in children:
            if hasattr(obj, '_children'):
                yield from Axes._legend_objects(obj._children)
            else:
                yield obj

    def _single_legend(self, pairs, ncol=None, order=None, **kwargs):
        """
        Draw an individual legend with support for changing legend-entries
        between column-major and row-major.
        """
        # Optionally change order
        # See: https://stackoverflow.com/q/10101141/4970632
        # Example: If 5 columns, but final row length 3, columns 0-2 have
        # N rows but 3-4 have N-1 rows.
        ncol = _not_none(ncol, 3)
        if order == 'C':
            nbase = len(pairs) // ncol + 1
            split = [pairs[i * ncol:(i + 1) * ncol] for i in range(nbase)]
            pairs = []
            nrows_max = len(split)  # max possible row count
            ncols_final = len(split[-1])  # columns in final row
            nrows = [nrows_max] * ncols_final + [nrows_max - 1] * (ncol - ncols_final)
            for col, nrow in enumerate(nrows):  # iterate through cols
                pairs.extend(split[row][col] for row in range(nrow))
        return mlegend.Legend(self, *zip(*pairs), ncol=ncol, **kwargs)

    def _multiple_legend(
        self, pairs, *, loc=None, title=None, fontsize=None, **kwargs
    ):
        """
        Draw "legend" with centered rows by creating separate legends for
        each row. The label spacing/border spacing will be exactly replicated.
        """
        # Issue warning when overriding some properties
        legs = []
        frameon = kwargs.pop('frameon', None)  # we add our own frame
        fontsize = _not_none(fontsize, rc['legend.fontsize'])
        overridden = []
        for override in ('bbox_transform', 'bbox_to_anchor'):
            prop = kwargs.pop(override, None)
            if prop is not None:
                overridden.append(override)
        if overridden:
            warnings._warn_proplot(
                'Ignoring user input properties '
                + ', '.join(map(repr, overridden))
                + ' for centered-row legend.'
            )

        # Determine space we want sub-legend to occupy as fraction of height
        # NOTE: Empirical testing shows spacing fudge factor necessary to
        # exactly replicate the spacing of standard aligned legends.
        width, height = self._get_size_inches()
        spacing = kwargs.get('labelspacing', None) or rc['legend.labelspacing']
        if pairs:
            interval = 1 / len(pairs)  # split up axes
            interval = (((1 + spacing * 0.85) * fontsize) / 72) / height

        # Iterate and draw
        # NOTE: We confine possible bounding box in *y*-direction, but do not
        # confine it in *x*-direction. Matplotlib will automatically move
        # left-to-right if you request this.
        loc = _not_none(loc, 'upper center')
        if not isinstance(loc, str):
            raise ValueError(
                f'Invalid location {loc!r} for legend with center=True. '
                'Must be a location *string*.'
            )
        elif loc == 'best':
            warnings._warn_proplot(
                'For centered-row legends, cannot use "best" location. '
                'Using "upper center" instead.'
            )
        for i, ipairs in enumerate(pairs):
            if i > 0 and title is not None:
                i += 1  # add extra space!
            if 'upper' in loc:
                y1 = 1 - (i + 1) * interval
                y2 = 1 - i * interval
            elif 'lower' in loc:
                y1 = (len(pairs) + i - 2) * interval
                y2 = (len(pairs) + i - 1) * interval
            else:  # center
                y1 = 0.5 + interval * len(pairs) / 2 - (i + 1) * interval
                y2 = 0.5 + interval * len(pairs) / 2 - i * interval
            bbox = mtransforms.Bbox([[0, y1], [1, y2]])
            leg = mlegend.Legend(
                self, *zip(*ipairs), loc=loc, ncol=len(ipairs),
                bbox_to_anchor=bbox, bbox_transform=self.transAxes,
                frameon=False, title=(title if i == 0 else None), **kwargs
            )
            legs.append(leg)

        # Draw manual fancy bounding box for un-aligned legend
        # WARNING: legendPatch uses the default transform, i.e. universal coordinates
        # in points. Means we have to transform mutation scale into transAxes sizes.
        # WARNING: Tempting to use legendPatch for everything but for some reason
        # coordinates are messed up. In some tests all coordinates were just result
        # of get window extent multiplied by 2 (???). Anyway actual box is found in
        # _legend_box attribute, which is accessed by get_window_extent.
        if not frameon:
            return legs  # no frame needed
        if len(legs) == 1:
            legs[0].set_frame_on(True)
            return legs  # use the native frame
        width, height = self._get_size_inches()
        renderer = self.figure._get_renderer()  # arbitrary renderer
        trans = self.transAxes.inverted()
        bboxs = [leg.get_window_extent(renderer).transformed(trans) for leg in legs]
        xmin = min(bbox.xmin for bbox in bboxs)
        xmax = max(bbox.xmax for bbox in bboxs)
        ymin = min(bbox.ymin for bbox in bboxs)
        ymax = max(bbox.ymax for bbox in bboxs)
        fontsize = (fontsize / 72) / width  # axes relative units
        fontsize = renderer.points_to_pixels(fontsize)

        # Draw and format patch
        # TODO: Shadow patch does not seem to work. Figure it out
        patch = mpatches.FancyBboxPatch(
            (xmin, ymin), xmax - xmin, ymax - ymin,
            snap=True, zorder=4.5,
            mutation_scale=fontsize,
            transform=self.transAxes
        )
        if kwargs.get('fancybox', rc['legend.fancybox']):
            patch.set_boxstyle('round', pad=0, rounding_size=0.2)
        else:
            patch.set_boxstyle('square', pad=0)
        patch.set_clip_on(False)
        self.add_artist(patch)
        if kwargs.get('shadow', rc['legend.shadow']):
            shadow = mpatches.Shadow(patch, 20, -20)
            self.add_artist(shadow)

        return (patch, *legs)

    def _draw_legend(
        self, handles=None, labels=None, *,
        loc=None, width=None, pad=None, space=None,
        frame=None, frameon=None, ncol=None, ncols=None,
        alphabetize=False, center=None, order='C', label=None, title=None,
        fontsize=None, fontweight=None, fontcolor=None,
        titlefontsize=None, titlefontweight=None, titlefontcolor=None, **kwargs
    ):
        """
        The driver function for adding axes legends.
        """
        # Parse input argument units
        ncol = _not_none(ncols=ncols, ncol=ncol)
        frameon = _not_none(frame=frame, frameon=frameon, default=rc['legend.frameon'])
        fontsize = _not_none(kwargs.pop('fontsize', None), rc['legend.fontsize'])
        titlefontsize = _not_none(
            title_fontsize=kwargs.pop('title_fontsize', None),
            titlefontsize=titlefontsize,
            default=rc['legend.title_fontsize']
        )
        fontsize = _fontsize_to_pt(fontsize)
        titlefontsize = _fontsize_to_pt(titlefontsize)
        if order not in ('F', 'C'):
            raise ValueError(
                f'Invalid order {order!r}. Choose from '
                '"C" (row-major, default) and "F" (column-major).'
            )

        # Convert relevant keys to em-widths
        for setting in rcsetup.EM_KEYS:  # em-width keys
            pair = setting.split('legend.', 1)
            if len(pair) == 1:
                continue
            _, key = pair
            value = kwargs.pop(key, None)
            if isinstance(value, str):
                value = units(kwargs[key], 'em', fontsize=fontsize)
            if value is not None:
                kwargs[key] = value

        # Generate and fill panel axes
        # NOTE: Important to remove None valued args above for these setdefault calls
        if loc in ('left', 'right', 'top', 'bottom'):
            lax = self.panel_axes(loc, width=width, space=space, pad=pad, filled=True)
            loc = 'fill'
        else:
            lax = self
            loc = loc
            if pad is not None:  # allow using 'pad' for 'borderaxespad'
                kwargs['borderaxespad'] = _not_none(
                    borderaxespad=kwargs.pop('borderaxespad', None),
                    pad=units(pad, 'em', fontsize=fontsize)
                )
        if loc == 'fill':
            lax._hide_panel()
            kwargs.setdefault('borderaxespad', 0)
            if not frameon:
                kwargs.setdefault('borderpad', 0)
            loc_sides = {  # translate 'filled' legends to location
                None: 'center',
                'left': 'center right',
                'right': 'center left',
                'top': 'lower center',
                'bottom': 'upper center',
            }
            loc = loc_sides[lax._panel_side]

        # Legend bounding box properties
        # NOTE: Here we permit only 'edgewidth' to avoid conflict with handle
        # property overrides.
        kw_patch = _pop_kwargs(
            kwargs,
            alpha=('a', 'framealpha', 'facealpha'),
            facecolor=('fc', 'framecolor'),
            edgecolor=('ec',),
            edgewidth=('ew',),
        )
        kw_outline_default = {
            'alpha': 'legend.framealpha',
            'facecolor': 'legend.facecolor',
            'edgecolor': 'legend.edgecolor',
            'edgewidth': 'axes.linewidth',
        }
        for key, name in kw_outline_default.items():
            kw_patch.setdefault(key, rc[name])
        kw_patch['linewidth'] = kw_patch.pop('edgewidth')

        # Handle and text properties that are applied after-the-fact
        # NOTE: Set solid_capstyle to 'butt' so line does not extend past error bounds
        # shading in legend entry. This change is not noticable in other situations.
        kw_handle = _pop_props(kwargs, 'collection')
        kw_handle['solid_capstyle'] = 'butt'
        kw_text = {}
        if fontcolor is not None:
            kw_text['color'] = fontcolor
        if fontweight is not None:
            kw_text['weight'] = fontweight
        kw_title = {}
        if titlefontcolor is not None:
            kw_title['color'] = titlefontcolor
        if titlefontweight is not None:
            kw_title['weight'] = titlefontweight

        # Parse the legend handles using axes for auto-handle detection
        # TODO: Update this when we no longer use "filled panels" for outer legends
        axs = [lax]
        if lax._panel_hidden:  # this is a "filled" legend
            if lax._panel_parent:  # axes panel i.e. axes-wide legend
                axs = list(lax._panel_parent._iter_axes(hidden=False, children=True))
            else:  # figure panel i.e. figure-wide legend
                axs = list(self.figure._iter_axes(hidden=False, children=True))
        pairs = self._parse_handles_labels(
            axs, handles, labels,
            ncol=ncol, order=order, center=center, alphabetize=alphabetize,
        )
        title = _not_none(label=label, title=title)

        # Create legend object(s)
        kwargs.update({
            'title': title,
            'frameon': frameon,
            'fontsize': fontsize,
            'title_fontsize': titlefontsize,
        })
        if not pairs:  # fallback
            objs = [mlegend.Legend(lax, [], [], **kwargs)]
        elif center:  # multi-legend pseudo-legend
            objs = lax._multiple_legend(pairs, loc=loc, **kwargs)
        else:  # standard legend
            objs = [lax._single_legend(pairs, loc=loc, ncol=ncol, **kwargs)]
        for obj in objs:
            if isinstance(obj, mpatches.FancyBboxPatch):
                continue
            if hasattr(lax, 'legend_') and lax.legend_ is None:
                lax.legend_ = obj  # set *first* legend accessible with get_legend()
            else:
                lax.add_artist(obj)

        # Update legend patch and elements
        # TODO: Remove handle overrides? Idea was this lets users create *categorical*
        # legends in clunky way, e.g. entries denoting *colors* and entries denoting
        # *markers*. But would be better to add capacity for categorical labels in a
        # *single* legend like seaborn rather than multiple legends.
        # WARNING: legendHandles only contains the *first* artist per legend because
        # HandlerBase.legend_artist() called in Legend._init_legend_box() only
        # returns the first artist. Instead we try to iterate through offset boxes.
        for obj in objs:
            # Update patch
            if not isinstance(obj, mpatches.FancyBboxPatch):
                obj.legendPatch.update(kw_patch)  # no-op if frame is off
            else:
                obj.update(kw_patch)  # the multiple-legend bounding box
                continue
            try:
                children = obj._legend_handle_box._children
            except AttributeError:  # older versions maybe?
                children = []
            # Update title text, handle text, and handle artist properties
            for obj in self._legend_objects(children):
                # NOTE: This silently other invalid properties
                if isinstance(obj, mtext.Text):
                    obj.update(kw_text)
                    continue
                for key, value in kw_handle.items():
                    getattr(obj, 'set_' + key, lambda value: None)(value)

        # Return after registering location
        for obj in objs:
            obj.set_clip_on(False)  # critical for tight bounding box calcs
        if isinstance(objs[0], mpatches.FancyBboxPatch):
            objs = objs[1:]
        obj = objs[0] if len(objs) == 1 else tuple(objs)
        self._add_guide('legend', obj, loc)  # possibly replace another
        return obj

    @docstring._concatenate_original
    @_snippet_manager
    def legend(
        self, handles=None, labels=None, *, loc=None, location=None, queue=False,
        **kwargs
    ):
        """
        Add an *inset* legend or *outer* legend along the edge of the axes.

        Parameters
        ----------
        %(axes.legend_args)s
        loc, location : int or str, optional
            The legend location. Default is :rc:`legend.loc`. Valid location
            keys are shown in the below table.

            .. _legend_table:

            ==================  =======================================
            Location            Valid keys
            ==================  =======================================
            outer left          ``'left'``, ``'l'``
            outer right         ``'right'``, ``'r'``
            outer bottom        ``'bottom'``, ``'b'``
            outer top           ``'top'``, ``'t'``
            "best" inset        ``'best'``, ``'inset'``, ``'i'``, ``0``
            upper right inset   ``'upper right'``, ``'ur'``, ``1``
            upper left inset    ``'upper left'``, ``'ul'``, ``2``
            lower left inset    ``'lower left'``, ``'ll'``, ``3``
            lower right inset   ``'lower right'``, ``'lr'``, ``4``
            center left inset   ``'center left'``, ``'cl'``, ``5``
            center right inset  ``'center right'``, ``'cr'``, ``6``
            lower center inset  ``'lower center'``, ``'lc'``, ``7``
            upper center inset  ``'upper center'``, ``'uc'``, ``8``
            center inset        ``'center'``, ``'c'``, ``9``
            "filled"            ``'fill'``
            ==================  =======================================

        width : float or str, optional
            For outer legends only. The space allocated for the legend box. This
            does nothing if the tight layout algorithm is active for the figure.
            %(units.in)s
        %(axes.legend_space)s

        Other parameters
        ----------------
        %(axes.legend_kwargs)s

        See also
        --------
        proplot.figure.Figure.legend
        matplotlib.axes.Axes.legend
        """
        # Either draw right now or queue up for later
        # Handles can be successively added to a single location this way. This
        # is used internally for on-the-fly legends.
        loc = _not_none(loc=loc, location=location)
        loc = _translate_loc(loc, 'legend', default=rc['legend.loc'])
        kwargs = _guide_kw_from_obj(handles, 'legend', kwargs)
        if queue:
            obj = (handles, labels)
            self._add_guide('legend', obj, loc, **kwargs)
        else:
            leg = self._draw_legend(handles, labels, loc=loc, **kwargs)
            return leg

    @staticmethod
    def _transfer_text(src, dest):
        """
        Transfer the input text object properties and content to the destination
        text object. Then clear the input object text.
        """
        text = src.get_text()
        dest.set_color(src.get_color())  # not a font property
        dest.set_fontproperties(src.get_fontproperties())  # size, weight, etc.
        if not text.strip():  # WARNING: must test strip() (see _align_axis_labels())
            return
        dest.set_text(text)
        src.set_text('')

    @staticmethod
    def _update_text(text, props=None, **kwargs):
        """
        Add a monkey patch for ``Text.update`` with pseudo "border" and "bbox"
        properties without wrapping the entire class. This facillitates inset titles.
        """
        props = props or {}
        props = props.copy()  # shallow copy
        props.update(kwargs)

        # Update border
        border = props.pop('border', None)
        bordercolor = props.pop('bordercolor', 'w')
        borderinvert = props.pop('borderinvert', False)
        borderwidth = props.pop('borderwidth', 2)
        if border:
            facecolor, bgcolor = text.get_color(), bordercolor
            if borderinvert:
                facecolor, bgcolor = bgcolor, facecolor
            kwargs = {
                'linewidth': borderwidth,
                'foreground': bgcolor,
                'joinstyle': 'miter',
            }
            text.set_color(facecolor)
            text.set_path_effects(
                [mpatheffects.Stroke(**kwargs), mpatheffects.Normal()],
            )
        elif border is False:
            text.set_path_effects(None)

        # Update bounding box
        # NOTE: We use '_title_pad' and '_title_above' for both titles and a-b-c
        # labels because always want to keep them aligned.
        # NOTE: For some reason using pad / 10 results in perfect alignment for
        # med-large labels. Tried scaling to be font size relative but never works.
        pad = text.axes._title_pad / 10  # default pad
        bbox = props.pop('bbox', None)
        bboxcolor = props.pop('bboxcolor', 'w')
        bboxstyle = props.pop('bboxstyle', 'round')
        bboxalpha = props.pop('bboxalpha', 0.5)
        bboxpad = _not_none(props.pop('bboxpad', None), pad)
        if isinstance(bbox, dict):  # *native* matplotlib usage
            props['bbox'] = bbox
        elif bbox:
            text.set_bbox({
                'edgecolor': 'black',
                'facecolor': bboxcolor,
                'boxstyle': bboxstyle,
                'alpha': bboxalpha,
                'pad': bboxpad,
            })
        elif bbox is False:
            text.set_bbox(None)  # disables the bbox

        return mtext.Text.update(text, props)

    @docstring._concatenate_original
    @_snippet_manager
    def text(
        self, *args,
        border=False, bordercolor='w', borderwidth=2, borderinvert=False,
        bbox=False, bboxcolor='w', bboxstyle='round', bboxalpha=0.5, bboxpad=None,
        fontfamily=None, family=None, fontname=None, name=None,
        fontsize=None, size=None, **kwargs
    ):
        """
        Add text to the axes.

        Parameters
        ----------
        x, y, [z] : float
            The coordinates for the text
        s : str
            The string for the text.
        transform \
: {{'data', 'axes', 'figure'}} or `~matplotlib.transforms.Transform`, optional
            The transform used to interpret `x` and `y`. This can be a
            `~matplotlib.transforms.Transform` object or a string corresponding to
            `~matplotlib.axes.Axes.transData`, `~matplotlib.axes.Axes.transAxes`,
            or `~matplotlib.figure.Figure.transFigure`. Default is ``'data'``,
            i.e. the text is positioned in data coordinates.

        Other parameters
        ----------------
        border : bool, optional
            Whether to draw border around text.
        borderwidth : float, optional
            The width of the text border. Default is ``2`` points.
        bordercolor : color-spec, optional
            The color of the text border. Default is ``'w'``.
        borderinvert : bool, optional
            If ``True``, the text and border colors are swapped.
        bbox : bool, optional
            Whether to draw a bounding box around text.
        bboxcolor : color-spec, optional
            The color of the text bounding box. Default is ``'w'``.
        bboxstyle : boxstyle, optional
            The style of the bounding box. Default is ``'round'``.
        bboxalpha : float, optional
            The alpha for the bounding box. Default is ``'0.5'``.
        bboxpad : float, optional
            The padding for the bounding box. Default is :rc:`title.bboxpad`.
        name, fontname
            Aliases for `family`, `fontfamily`.
        family, fontfamily : str, optional
            The font typeface name (e.g., ``'Fira Math'``) or font family name (e.g.,
            ``'serif'``). Matplotlib falls back to the system default if not found.
        size, fontsize : float or str, optional
            The font size. %(units.pt)s
            This can also be a string indicating some scaling relative to
            :rcraw:`font.size`. The sizes and scalings are shown below. The
            scalings ``'med'``, ``'med-small'``, and ``'med-large'`` are
            added by ProPlot while the rest are native matplotlib sizes.

            .. _font_table:

            ==========================  =====
            Size                        Scale
            ==========================  =====
            ``'xx-small'``              0.579
            ``'x-small'``               0.694
            ``'small'``, ``'smaller'``  0.833
            ``'med-small'``             0.9
            ``'med'``, ``'medium'``     1.0
            ``'med-large'``             1.1
            ``'large'``, ``'larger'``   1.2
            ``'x-large'``               1.440
            ``'xx-large'``              1.728
            ``'larger'``                1.2
            ==========================  =====

        **kwargs
            Passed to `matplotlib.axes.Axes.text`.

        See also
        --------
        matplotlib.axes.Axes.text
        """
        # Translate positional args
        # Audo-redirect to text2D for 3D axes if not enough arguments passed
        # NOTE: The transform must be passed positionally for 3D axes with 2D coords
        keys = tuple('xyz' if self.name == 'proplot_three' else 'xy')
        keys += (('s', 'text'),)  # interpret both 's' and 'text'
        args, kwargs = _keyword_to_positional(keys, *args, **kwargs)
        if len(args) == len(keys) + 1:
            add_text = super().text
            *args, transform = args
        elif len(args) == len(keys):
            add_text = super().text
            transform = kwargs.pop('transform', None)
        elif len(args) == len(keys) - 1 and self.name == 'proplot_three':
            add_text = self.text2D
            transform = kwargs.pop('transform', None)
        else:
            raise TypeError(
                f'Expected {len(keys) - 1} to {len(keys)} positional '
                f'arguments but got {len(args)}.'
            )

        # Translate keyword args
        # TODO: Translate all properties and emit warnings?
        size = _not_none(size, fontsize)
        family = _not_none(fontname, name, fontfamily, family)
        if size is not None:
            kwargs['size'] = _fontsize_to_pt(size)
        if family is not None:
            kwargs['fontfamily'] = family
        if transform is None:
            transform = self.transData
        else:
            transform = self._get_transform(transform)

        # Update the text object using monkey patch
        obj = add_text(*args, transform=transform, **kwargs)
        obj.update = self._update_text.__get__(obj)
        obj.update({
            'border': border,
            'bordercolor': bordercolor,
            'borderinvert': borderinvert,
            'borderwidth': borderwidth,
            'bbox': bbox,
            'bboxcolor': bboxcolor,
            'bboxstyle': bboxstyle,
            'bboxalpha': bboxalpha,
            'bboxpad': bboxpad,
        })
        return obj

    def _iter_axes(self, hidden=False, children=False, panels=True):
        """
        Return a list of visible axes, panel axes, and child axes of both.

        Parameters
        ----------
        hidden : bool, optional
            Whether to include "hidden" panels.
        children : bool, optional
            Whether to include children. Note this now includes "twin" axes.
        panels : bool or str or list of str, optional
            Whether to include panels or the panels to include.
        """
        # Parse panels
        if panels is False:
            panels = ()
        elif panels is True or panels is None:
            panels = ('left', 'right', 'bottom', 'top')
        elif isinstance(panels, str):
            panels = (panels,)
        if not set(panels) <= {'left', 'right', 'bottom', 'top'}:
            raise ValueError(f'Invalid sides {panels!r}.')
        # Iterate
        axs = (self, *(ax for side in panels for ax in self._panel_dict[side]))
        for iax in axs:
            if not hidden and iax._panel_hidden:
                continue  # ignore hidden panel and its colorbar/legend child
            iaxs = (iax, *(iax.child_axes if children else ()))
            for jax in iaxs:
                if not jax.get_visible():
                    continue  # safety first
                yield jax

    @property
    def number(self):
        """
        The axes number. This controls the order of a-b-c labels and the
        order of appearence in the `~proplot.figure.SubplotGrid` returned by
        `proplot.figure.Figure.subplots` and `proplot.ui.subplots`.
        """
        return self._number

    @number.setter
    def number(self, num):
        if num is None or isinstance(num, Integral) and num > 0:
            self._number = num
        else:
            raise ValueError(f'Invalid number {num!r}. Must be integer >=1.')
