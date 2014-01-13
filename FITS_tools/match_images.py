import numpy as np
try:
    import astropy.io.fits as pyfits
    import astropy.wcs as pywcs
except ImportError:
    import pyfits
    import pywcs
from .strip_headers import flatten_header

def project_to_header(fitsfile, header, use_montage=True, quiet=True, **kwargs):
    """
    Light wrapper of montage with hcongrid as a backup

    kwargs will be passed to hcongrid if `use_montage==False`

    Parameters
    ----------
        fitsfile : string
            a FITS file name
        header : pyfits.Header
            A pyfits Header instance with valid WCS to project to
        use_montage : bool
            Use montage or hcongrid (scipy's map_coordinates)
        quiet : bool
            Silence Montage's output

    Returns
    -------
        np.ndarray image projected to header's coordinates

    """
    try:
        import montage
        montageOK=True
    except ImportError:
        montageOK=False
    try:
        from hcongrid import hcongrid
        hcongridOK=True
    except ImportError:
        hcongridOK=False
    import tempfile

    if montageOK and use_montage:
        temp_headerfile = tempfile.NamedTemporaryFile()
        header.toTxtFile(temp_headerfile.name)

        outfile = tempfile.NamedTemporaryFile()
        montage.wrappers.reproject(fitsfile, outfile.name,
                temp_headerfile.name, exact_size=True,
                silent_cleanup=quiet)
        image = pyfits.getdata(outfile.name)
        
        outfile.close()
        temp_headerfile.close()
    elif hcongridOK:
        # only works for 2D images
        image = hcongrid(pyfits.getdata(fitsfile).squeeze(),
                         flatten_header(pyfits.getheader(fitsfile)),
                         header,
                         **kwargs)

    return image

def match_fits(fitsfile1, fitsfile2, header=None, sigma_cut=False,
        return_header=False, **kwargs):
    """
    Project one FITS file into another's coordinates
    If sigma_cut is used, will try to find only regions that are significant
    in both images using the standard deviation

    Parameters
    ----------
    fitsfile1: str
        Reference fits file name
    fitsfile2: str
        Offset fits file name
    header: pyfits.Header
        Optional - can pass a header to projet both images to
    sigma_cut: bool or int
        Perform a sigma-cut on the returned images at this level

    Returns
    -------
    image1,image2,[header] : 
        Two images projected into the same space, and optionally
        the header used to project them
    """

    if header is None:
        header = flatten_header(pyfits.getheader(fitsfile1))
        image1 = pyfits.getdata(fitsfile1).squeeze()
    else: # project image 1 to input header coordinates
        image1 = project_to_header(fitsfile1, header, **kwargs)

    # project image 2 to image 1 coordinates
    image2_projected = project_to_header(fitsfile2, header, **kwargs)

    if image1.shape != image2_projected.shape:
        raise ValueError("Failed to reproject images to same shape.")

    if sigma_cut:
        corr_image1 = image1*(image1 > image1.std()*sigma_cut)
        corr_image2 = image2_projected*(image2_projected > image2_projected.std()*sigma_cut)
        OK = (corr_image1==corr_image1)*(corr_image2==corr_image2) 
        if (corr_image1[OK]*corr_image2[OK]).sum() == 0:
            print "Could not use sigma_cut of %f because it excluded all valid data" % sigma_cut
            corr_image1 = image1
            corr_image2 = image2_projected
    else:
        corr_image1 = image1
        corr_image2 = image2_projected

    returns = corr_image1, corr_image2
    if return_header:
        returns = returns + (header,)
    return returns
