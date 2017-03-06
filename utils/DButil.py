import numpy as np

__author__ = ["Sijie Yu"]
__email__ = "sijie.yu@njit.edu"


def getfreeport():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def sdo_aia_scale(image=None, wavelength=None):
    '''
    rescale the aia image
    :param image: normalised aia image data
    :param wavelength:
    :return: byte scaled image data
    '''
    from scipy.misc import bytescale
    if wavelength == '94':
        image[image > 30] = 30
        image[image < 0.5] = 0.5
        image = np.log10(image)
    elif wavelength == '131':
        image[image > 200] = 200
        image[image < 2] = 2
        image = np.log10(image)
    elif wavelength == '171':
        image[image > 4000] = 4000
        image[image < 20] = 20
        image = np.log10(image)
    return bytescale(image)


def insertchar(source_str, insert_str, pos):
    return source_str[:pos] + insert_str + source_str[pos:]


def readsdofile(datadir=None, wavelength=None, jdtime=None, isexists=False, timtol=1):
    '''
    read sdo file from local database
    :param datadir:
    :param wavelength:
    :param jdtime: the timestamp
    :param isexists: check if file exist. no data return.
    :param timtol: time difference tolerance in days for considering data as the same timestamp
    :return:
    '''
    import glob
    import os
    from astropy.time import Time
    import sunpy.map
    sdofitspath = glob.glob(datadir + '/aia.lev1_*Z.{}.image_lev1.fits'.format(wavelength))
    sdofits = [os.path.basename(ll) for ll in sdofitspath]
    sdotimeline = Time([insertchar(insertchar(ll.split('.')[2].replace('T', ' ').replace('Z', ''), ':', -4), ':', -2)
                        for
                        ll in sdofits], format='iso', scale='utc')

    if 12. / 3600 / 24 < timtol < np.min(np.abs(sdotimeline.jd - jdtime)):
        raise ValueError('SDO File not found at the select timestamp. Download the data with EvtBrowser first.')
    idxaia = np.argmin(np.abs(sdotimeline.jd - jdtime))
    sdofile = sdofitspath[idxaia]
    if isexists:
        return os.path.exists(sdofile)
    else:
        try:
            sdomap = sunpy.map.Map(sdofile)
            return sdomap
        except:
            raise ValueError('File not found or invalid input')


def findDist(x, y):
    dx = np.diff(x)
    dy = np.diff(y)
    dist = np.hypot(dx, dy)
    return np.insert(dist, 0, 0.0)


def paramspline(x, y, length, s=0):
    from scipy.interpolate import splev, splprep
    tck, u = splprep([x, y], s=s)
    unew = np.linspace(0, u[-1], length)
    out = splev(unew, tck)
    xs, ys = out[0], out[1]
    grads = get_curve_grad(xs, ys)
    return {'xs': xs, 'ys': ys, 'grads': grads['grad'], 'posangs': grads['posang']}


def polyfit(x, y, length, deg):
    xs = np.linspace(x.min(), x.max(), length)
    z = np.polyfit(x=x, y=y, deg=deg)
    p = np.poly1d(z)
    ys = p(xs)
    grads = get_curve_grad(xs, ys)
    return {'xs': xs, 'ys': ys, 'grads': grads['grad'], 'posangs': grads['posang']}


def spline(x, y, length, s=0):
    from scipy.interpolate import splev, splrep
    xs = np.linspace(x.min(), x.max(), length)
    tck = splrep(x, y, s=s)
    ys = splev(xs, tck)
    grads = get_curve_grad(xs, ys)
    return {'xs': xs, 'ys': ys, 'grads': grads['grad'], 'posangs': grads['posang']}


def get_curve_grad(x, y):
    '''
    get the grad of at data point
    :param x:
    :param y:
    :return: grad,posang
    '''
    deltay = np.roll(y, -1) - np.roll(y, 1)
    deltay[0] = y[1] - y[0]
    deltay[-1] = y[-1] - y[-2]
    deltax = np.roll(x, -1) - np.roll(x, 1)
    deltax[0] = x[1] - x[0]
    deltax[-1] = x[-1] - x[-2]
    grad = deltay / deltax
    posang = np.arctan2(deltay, deltax)
    return {'grad': grad, 'posang': posang}


def improfile(z, xi, yi, interp='cubic'):
    '''
    Pixel-value cross-section along line segment in an image
    :param z: an image array
    :param xi and yi: equal-length vectors specifying the pixel coordinates of the endpoints of the line segment
    :param interp: interpolation type to sampling, 'nearest' or 'cubic'
    :return: the intensity values of pixels along the line
    '''
    import scipy.ndimage
    imgshape = z.shape
    # x = np.arange(imgshape[1])
    # y = np.arange(imgshape[0])
    if len(xi) != len(yi):
        raise ValueError('xi and yi must be equal-length!')
    if len(xi) < 2:
        raise ValueError('xi or yi must contain at least two elements!')
    for idx, ll in enumerate(xi):
        if not 0 < ll < imgshape[1] - 1:
            raise ValueError('xi out of range!')
        if not 0 < yi[idx] < imgshape[0] - 1:
            raise ValueError('yi out of range!')
            # xx, yy = np.meshgrid(x, y)
    if len(xi) == 2:
        length = np.hypot(np.diff(xi), np.diff(yi))[0]
        x, y = np.linspace(xi[0], xi[1], length), np.linspace(yi[0], yi[1], length)
    else:
        x, y = xi, yi
    if interp == 'cubic':
        zi = scipy.ndimage.map_coordinates(z, np.vstack((x, y)))
    else:
        zi = z[x.astype(np.int), y.astype(np.int)]

    return zi


def canvaspix_to_data(smap, x, y):
    import astropy.units as u
    '''
    Convert canvas pixel coordinates in MkPlot to data (world) coordinates by using
    `~astropy.wcs.WCS.wcs_pix2world`.

    :param smap: sunpy map
    :param x: canvas Pixel coordinates of the CTYPE1 axis. (Normally solar-x)
    :param y: canvas Pixel coordinates of the CTYPE2 axis. (Normally solar-y)
    :return: world coordinates
    '''
    xynew = smap.pixel_to_data(x * u.pix, y * u.pix)
    xnew = xynew[0].value
    ynew = xynew[1].value
    return [xnew,ynew]

def data_to_mappixel(smap, x, y):
    import astropy.units as u
    '''
    Convert data (world) coordinates in MkPlot to pixel coordinates in smap by using
    `~astropy.wcs.WCS.wcs_pix2world`.

    :param smap: sunpy map
    :param x: Data coordinates of the CTYPE1 axis. (Normally solar-x)
    :param y: Data coordinates of the CTYPE2 axis. (Normally solar-y)
    :return: pixel coordinates
    '''
    xynew = smap.data_to_pixel(x * u.arcsec, y * u.arcsec)
    xnew = xynew[0].value
    ynew = xynew[1].value
    return [xnew,ynew]


def polsfromfitsheader(header):
    '''
    get polarisation information from fits header
    :param header: fits header
    :return pols: polarisation stokes
    '''
    try:
        stokeslist = ['{}'.format(int(ll)) for ll in
                      (header["CRVAL4"] + np.arange(header["NAXIS4"]) * header["CDELT4"])]
        stokesdict = {'1': 'I', '2': 'Q', '3': 'U', '4': 'V', '-1': 'RR', '-2': 'LL', '-3': 'RL', '-4': 'LR',
                      '-5': 'XX', '-6': 'YY', '-7': 'XY', '-8': 'YX'}
        pols = map(lambda x: stokesdict[x], stokeslist)
    except:
        print("error in fits header!")
    return pols


def freqsfromfitsheader(header):
    '''
    get frequency in GHz from fits header
    :param header: fits header
    :return pols: polarisation stokes
    '''
    try:
        freqs = ['{:.3f}'.format(ll / 1e9) for ll in
                 (header["CRVAL3"] + np.arange(header["NAXIS3"]) * header["CDELT3"])]
        return freqs
    except:
        print("error in fits header!")
        raise ValueError


def transfitdict2DF(datain, gaussfit=True):
    '''
    convert the results from pimfit or pmaxfit tasks to pandas DataFrame structure.
    :param datain: The component list from pimfit or pmaxfit tasks
    :param gaussfit: True if the results is from pimfit, otherwise False.
    :return: the pandas DataFrame structure.
    '''
    import pandas as pd

    ra2arcsec = 180. * 3600. / np.pi
    dspecDF0 = pd.DataFrame()
    for ll in datain['timestamps']:
        tidx = datain['timestamps'].index(ll)
        if datain['succeeded'][tidx]:
            pols = datain['outputs'][tidx].keys()
            dspecDFlist = []
            dspecDF = pd.DataFrame()
            for ppit in pols:
                dspecDFtmp = pd.DataFrame()
                shape_latitude = []
                shape_longitude = []
                shape_latitude_err = []
                shape_longitude_err = []
                shape_majoraxis = []
                shape_minoraxis = []
                shape_positionangle = []
                peak = []
                beam_major = []
                beam_minor = []
                beam_positionangle = []
                freqstrs = []
                fits_local = []
                for comp in datain['outputs'][tidx][ppit]['results'].keys():
                    if comp.startswith('component'):
                        if gaussfit:
                            majoraxis = datain['outputs'][tidx][ppit]['results'][comp]['shape']['majoraxis']['value']
                            minoraxis = datain['outputs'][tidx][ppit]['results'][comp]['shape']['minoraxis']['value']
                            positionangle = datain['outputs'][tidx][ppit]['results'][comp]['shape']['positionangle'][
                                'value']
                            bmajor = datain['outputs'][tidx][ppit]['results'][comp]['beam']['beamarcsec']['major'][
                                'value']
                            bminor = datain['outputs'][tidx][ppit]['results'][comp]['beam']['beamarcsec']['minor'][
                                'value']
                            bpositionangle = \
                                datain['outputs'][tidx][ppit]['results'][comp]['beam']['beamarcsec']['positionangle'][
                                    'value']
                            shape_majoraxis.append(majoraxis)
                            shape_minoraxis.append(minoraxis)
                            shape_positionangle.append(positionangle)
                            beam_major.append(bmajor)
                            beam_minor.append(bminor)
                            beam_positionangle.append(bpositionangle)
                            fluxpeak = datain['outputs'][tidx][ppit]['results'][comp]['peak']['value']
                        else:
                            fluxpeak = datain['outputs'][tidx][ppit]['results'][comp]['flux']['value'][0]
                        longitude = datain['outputs'][tidx][ppit]['results'][comp]['shape']['direction']['m0'][
                                        'value'] * ra2arcsec
                        latitude = datain['outputs'][tidx][ppit]['results'][comp]['shape']['direction']['m1'][
                                       'value'] * ra2arcsec
                        longitude_err = \
                            datain['outputs'][tidx][ppit]['results'][comp]['shape']['direction']['error']['longitude'][
                                'value']
                        latitude_err = \
                            datain['outputs'][tidx][ppit]['results'][comp]['shape']['direction']['error']['latitude'][
                                'value']
                        shape_longitude.append(longitude)
                        shape_latitude.append(latitude)
                        shape_longitude_err.append(longitude_err)
                        shape_latitude_err.append(latitude_err)
                        peak.append(fluxpeak)
                        freqstrs.append('{:.3f}'.format(
                            datain['outputs'][tidx][ppit]['results'][comp]['spectrum']['frequency']['m0']['value']))
                        fits_local.append(datain['imagenames'][tidx].split('/')[-1])
                if gaussfit:
                    dspecDFtmp['shape_latitude{}'.format(ppit)] = pd.Series(shape_latitude)
                    dspecDFtmp['shape_longitude{}'.format(ppit)] = pd.Series(shape_longitude)
                    dspecDFtmp['shape_latitude_err{}'.format(ppit)] = pd.Series(shape_latitude_err)
                    dspecDFtmp['shape_longitude_err{}'.format(ppit)] = pd.Series(shape_longitude_err)
                    dspecDFtmp['peak{}'.format(ppit)] = pd.Series(peak)
                    dspecDFtmp['shape_majoraxis{}'.format(ppit)] = pd.Series(shape_majoraxis)
                    dspecDFtmp['shape_minoraxis{}'.format(ppit)] = pd.Series(shape_minoraxis)
                    dspecDFtmp['shape_positionangle{}'.format(ppit)] = pd.Series(shape_positionangle)
                    dspecDFtmp['beam_major{}'.format(ppit)] = pd.Series(beam_major)
                    dspecDFtmp['beam_minor{}'.format(ppit)] = pd.Series(beam_minor)
                    dspecDFtmp['beam_positionangle{}'.format(ppit)] = pd.Series(beam_positionangle)
                else:
                    dspecDFtmp['shape_latitude{}'.format(ppit)] = pd.Series(shape_latitude)
                    dspecDFtmp['shape_longitude{}'.format(ppit)] = pd.Series(shape_longitude)
                    dspecDFtmp['shape_latitude_err{}'.format(ppit)] = pd.Series(shape_latitude_err)
                    dspecDFtmp['shape_longitude_err{}'.format(ppit)] = pd.Series(shape_longitude_err)
                    dspecDFtmp['peak{}'.format(ppit)] = pd.Series(peak)
                dspecDFtmp['freqstr'.format(ppit)] = pd.Series(freqstrs)
                dspecDFtmp['fits_local'.format(ppit)] = pd.Series(fits_local)
                dspecDFlist.append(dspecDFtmp)
            for DFidx, DFit in enumerate(dspecDFlist):
                if DFidx == 0:
                    dspecDF = dspecDFlist[0]
                else:
                    dspecDF = pd.merge(dspecDF.copy(), DFit, how='outer', on=['freqstr', 'fits_local'])
            dspecDF0 = dspecDF0.append(dspecDF, ignore_index=True)

    return dspecDF0


def getcolctinDF(dspecDF, col):
    '''
    return the count of how many times of the element starts with col occurs in columns of dspecDF
    :param dspecDF:
    :param col: the start string
    :return: the count and items
    '''
    itemset1 = col
    itemset2 = dspecDF.columns.tolist()
    items = []
    for ll in itemset2:
        if ll.startswith(itemset1):
            items.append(ll)
    itemct = [ll.startswith(itemset1) for ll in itemset2].count(True)
    columns = items
    return [itemct, columns]


def dspecDFfilter(dspecDF, pol):
    '''
    filter the unselect polarisation from dspecDF
    :param dspecDF: the original dspecDF
    :param pol: selected polarisation, dtype = string
    :return: the output dspecDF
    '''
    colnlistcom = ['shape_latitude', 'shape_longitude', 'peak', 'shape_latitude_err', 'shape_longitude_err']
    colnlistgaus = ['shape_majoraxis', 'shape_minoraxis', 'shape_positionangle', 'beam_major', 'beam_minor',
                    'beam_positionangle']
    ## above are the columns to filter
    colnlistess = dspecDF.columns.tolist()
    if getcolctinDF(dspecDF, 'peak')[0] > 1:
        for ll in colnlistcom + colnlistgaus:
            colinfo = getcolctinDF(dspecDF, ll)
            if colinfo[0] > 0:
                for cc in colinfo[1]:
                    if cc in colnlistess:
                        colnlistess.remove(cc)
        dspecDF1 = dspecDF.copy()[colnlistess]
        for ll in colnlistcom:
            dspecDF1[ll] = dspecDF.copy()[ll + pol]
        if getcolctinDF(dspecDF, 'shape_majoraxis')[0] > 0:
            for ll in colnlistgaus:
                dspecDF1[ll] = dspecDF.copy()[ll + pol]
        return dspecDF1
    else:
        return dspecDF


def get_contour_data(X, Y, Z):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    from bokeh.models import (ColumnDataSource)
    cs = plt.contour(X, Y, Z, levels=(np.arange(5, 10, 2) / 10.0 * np.nanmax(Z)).tolist(), cmap=cm.Greys_r)
    xs = []
    ys = []
    xt = []
    yt = []
    col = []
    text = []
    isolevelid = 0
    for isolevel in cs.collections:
        # isocol = isolevel.get_color()[0]
        # thecol = 3 * [None]
        theiso = '{:.0f}%'.format(cs.get_array()[isolevelid] / Z.max() * 100)
        isolevelid += 1
        # for i in xrange(3):
        # thecol[i] = int(255 * isocol[i])
        thecol = '#%02x%02x%02x' % (220, 220, 220)
        # thecol = '#03FFF9'

        for path in isolevel.get_paths():
            v = path.vertices
            x = v[:, 0]
            y = v[:, 1]
            xs.append(x.tolist())
            ys.append(y.tolist())
            xt.append(x[len(x) / 2])
            yt.append(y[len(y) / 2])
            text.append(theiso)
            col.append(thecol)

    source = ColumnDataSource(data={'xs': xs, 'ys': ys, 'line_color': col, 'xt': xt, 'yt': yt, 'text': text})
    return source


def twoD_Gaussian((x, y), amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
    xo = float(xo)
    yo = float(yo)
    a = (np.cos(theta) ** 2) / (2 * sigma_x ** 2) + (np.sin(theta) ** 2) / (2 * sigma_y ** 2)
    b = -(np.sin(2 * theta)) / (4 * sigma_x ** 2) + (np.sin(2 * theta)) / (4 * sigma_y ** 2)
    c = (np.sin(theta) ** 2) / (2 * sigma_x ** 2) + (np.cos(theta) ** 2) / (2 * sigma_y ** 2)
    g = offset + amplitude * np.exp(- (a * ((x - xo) ** 2) + 2 * b * (x - xo) * (y - yo) + c * ((y - yo) ** 2)))
    return g.ravel()


def c_correlate(a, v):
    a = (a - np.mean(a)) / (np.std(a) * len(a))
    v = (v - np.mean(v)) / np.std(v)
    return np.correlate(a, v, mode='same')


def XCorrMap(z, x, y, doxscale=True):
    '''
    get the cross correlation map along y axis
    :param z: data
    :param x: x axis
    :param y: y axis
    :return:
    '''
    from scipy.interpolate import splev, splrep
    if doxscale:
        xfit = np.linspace(x[0], x[-1], 10 * len(x) + 1)
        zfit = np.zeros((len(y), len(xfit)))
        for yidx1, yq in enumerate(y):
            xx = x
            yy = z[yidx1, :]
            s = len(yy)  # (len(yy) - np.sqrt(2 * len(yy)))*2
            tck = splrep(xx, yy, s=s)
            ys = splev(xfit, tck)
            zfit[yidx1, :] = ys
    else:
        xfit = x
        zfit = z
    ny, nxfit = zfit.shape
    ccpeak = np.empty((ny - 1, ny - 1))
    ccpeak[:] = np.nan
    ccmax = ccpeak.copy()
    ya = ccpeak.copy()
    yv = ccpeak.copy()
    yidxa = ccpeak.copy()
    yidxv = ccpeak.copy()
    for idx1 in xrange(1, ny):
        for idx2 in xrange(0, idx1):
            lightcurve1 = zfit[idx1, :]
            lightcurve2 = zfit[idx2, :]
            ccval = c_correlate(lightcurve1, lightcurve2)
            if sum(lightcurve1) != 0 and sum(lightcurve2) != 0:
                cmax = np.amax(ccval)
                cpeak = np.argmax(ccval) - (nxfit - 1) / 2
            else:
                cmax = 0
                cpeak = 0
            ccmax[idx2, idx1 - 1] = cmax
            ccpeak[idx2, idx1 - 1] = cpeak
            ya[idx2, idx1 - 1] = y[idx1 - 1]
            yv[idx2, idx1 - 1] = y[idx2]
            yidxa[idx2, idx1 - 1] = idx1 - 1
            yidxv[idx2, idx1 - 1] = idx2
            if idx1 - 1 != idx2:
                ccmax[idx1 - 1, idx2] = cmax
                ccpeak[idx1 - 1, idx2] = cpeak
                ya[idx1 - 1, idx2] = y[idx2]
                yv[idx1 - 1, idx2] = y[idx1 - 1]
                yidxa[idx1 - 1, idx2] = idx2
                yidxv[idx1 - 1, idx2] = idx1 - 1

    return {'zfit': zfit, 'ccmax': ccmax, 'ccpeak': ccpeak, 'x': x, 'nx': len(x), 'xfit': xfit, 'nxfit': nxfit, 'y': y,
            'ny': ny, 'yv': yv, 'ya': ya, 'yidxv': yidxv, 'yidxa': yidxa}


class buttons_play:
    '''
    Produce A play/stop button widget for bokeh plot

    '''
    __slots__ = ['buttons']

    def __init__(self, plot_width=None, *args,
                 **kwargs):
        from bokeh.models import Button
        BUT_first = Button(label='<<', width=plot_width, button_type='primary')
        BUT_prev = Button(label='|<', width=plot_width, button_type='warning')
        BUT_play = Button(label='>', width=plot_width, button_type='success')
        BUT_next = Button(label='>|', width=plot_width, button_type='warning')
        BUT_last = Button(label='>>', width=plot_width, button_type='primary')

        self.buttons = [BUT_first, BUT_prev, BUT_play, BUT_next, BUT_last]

    def play(self, *args, **kwargs):
        if self.buttons[2].label == '>':
            self.buttons[2].label = '||'
        else:
            self.buttons[2].label = '>'
