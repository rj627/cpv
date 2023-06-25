"""
environment: (py38_ariadne)
Citations: https://github.com/jvines/astroARIADNE/blob/master/citations.md
"""

from astroARIADNE.star import Star
from astroARIADNE.fitter import Fitter
from astroARIADNE.plotter import SEDPlotter

import os
from os.path import join
import pandas as pd, numpy as np

from complexrotators.observability import get_gaia_rows
from complexrotators.paths import RESULTSDIR

from astropy.coordinates import SkyCoord
from astropy import units as u
from astroquery.vizier import Vizier

def run_SED_analysis(ticid, trimlist=None):
    """
    Run CQV-specific SED analysis.  Priors assume the star is a nearby M-dwarf.
    Output goes to /reuslts/ariadne_sed_fitting/{starname}

    Atmospheric models used are BT-Settl AGSS2009.

    Fitzpatrick extinction is assumed.

    Bailer-Jones Gaia EDR3 distance is assumed.

    Args:
        ticid (str): e.g. "402980664"

    Kwargs: list of quad tuples, each entry in form (>xmin, <xmax, >ymin, <ymax).
    E.g., to exclude everything above 1e-9 erg/cm2/s, and below 0.4 micron in
    the SED fit:
        [ (None, None, 1e-9, None) ,
          (None, 0.4, None, None) ],
        which is equivalent to
        [ (None, 0.4, 1e-9, None) ],
    """
    print(42*'-')
    print(f'Beginning {ticid}')
    ##################
    # query the star #
    ##################
    gdr2_df = get_gaia_rows(ticid, allcols=1)

    ra = float(gdr2_df.ra)
    dec = float(gdr2_df.dec)
    starname = f'TIC_{ticid}'
    g_id = int(gdr2_df.dr2_source_id)

    out_folder = join(RESULTSDIR, 'ariadne_sed_fitting', f'{starname}')
    if not os.path.exists(out_folder): os.mkdir(out_folder)

    s = Star(starname.replace("_"," "), ra, dec, g_id=g_id)

    # remove TESS mag; no new information
    s.remove_mag('TESS')

    # remove mags likely to be biased by UV excess (see eg Ingleby+2013, ApJ)
    # leave in Gaia BP because it's mostly fine

    s.remove_mag("STROMGREN_u")
    s.remove_mag("STROMGREN_b")
    s.remove_mag("STROMGREN_v")

    s.remove_mag('SkyMapper_u')
    s.remove_mag('SkyMapper_g')

    s.remove_mag('SDSS_u')
    s.remove_mag('SDSS_g')

    s.remove_mag('GALEX_FUV')
    s.remove_mag('GALEX_NUV')

    s.remove_mag('GROUND_JOHNSON_U')
    s.remove_mag('GROUND_JOHNSON_B')

    # remove skymapper; these seem biased vs other surveys like SDSS
    s.remove_mag('SkyMapper_i')
    s.remove_mag('SkyMapper_z')

    #
    # trim manually passed outliers (e.g. from crowded photometric fields)
    #
    if isinstance(trimlist, list):

        sel = s.mags != 0

        x = s.wave[sel]
        y = (s.flux*s.wave)[sel]
        n = s.filter_names[sel]

        mask = np.zeros_like(x).astype(bool)

        for trimentry in trimlist:

            xmin, xmax, ymin, ymax = trimentry

            if xmin is not None:
                mask |= x > xmin
            if xmax is not None:
                mask |= x < xmin
            if ymin is not None:
                mask |= y > ymin
            if ymax is not None:
                mask |= y < ymax

        mask_names = n[mask]

        for mask_name in mask_names:
            s.remove_mag(mask_name)


    #
    # add WISE W3 and W4; for SED visualization only (not used in fitting); cache too
    #
    c = SkyCoord(ra=ra, dec=dec, unit=(u.deg, u.deg))
    v = Vizier(columns=["*", "+_r"], catalog="II/328/allwise")
    result = v.query_region(c, frame='icrs', radius="10s")

    outcsv = join(out_folder, f"{starname}_allwise_query_results.csv")
    if len(result) == 0:
        outdf = pd.DataFrame({})
        print(f"Did not find WISE match; cache null to {outcsv}")
        outdf.to_csv(outcsv)
        W3mag, W4mag, e_W3mag, e_W4mag = None, None, None, None
    else:
        outdf = result[0].to_pandas()
        outdf = outdf.sort_values(by='W1mag')
        # take the brightest star as result
        outdf.to_csv(outcsv, index=False)
        print(f"Got WISE match; cache to {outcsv}")
        r = outdf.head(n=1)
        W3mag, W4mag, e_W3mag, e_W4mag = (
            float(r['W3mag']), float(r['W4mag']),
            float(r['e_W3mag']), float(r['e_W4mag'])
        )
        if (not pd.isnull(W3mag)) and (not pd.isnull(e_W3mag)):
            s.add_mag(W3mag, e_W3mag, 'WISE_RSR_W3')
        if (not pd.isnull(W4mag)) and (not pd.isnull(e_W4mag)):
            s.add_mag(W4mag, e_W4mag, 'WISE_RSR_W4')

    ######################
    # fit the photometry #
    ######################

    engine = 'dynesty'
    nlive = 500
    dlogz = 0.5
    bound = 'multi'
    sample = 'rwalk'
    threads = 4
    dynamic = False

    setup = [engine, nlive, dlogz, bound, sample, threads, dynamic]

    # Feel free to uncomment any unneeded/unwanted models
    models = [
        #'phoenix',
        'btsettl',
        #'btnextgen',
        #'btcond',
        #'kurucz',
        #'ck04'
    ]

    f = Fitter()
    f.star = s
    f.setup = setup
    f.av_law = 'fitzpatrick'
    f.out_folder = out_folder
    f.bma = True
    f.models = models
    f.n_samples = 100000

    # The default prior for Teff is an empirical prior drawn from the RAVE survey
    # temperatures distribution, the distance prior is drawn from the Bailer-Jones
    # distance estimate from Gaia EDR3, and the radius has a flat prior ranging from
    # 0.5 to 20 R$_\odot$. The default prior for the metallicity z and log g are also
    # their respective distributions from the RAVE survey, the default prior for Av
    # is a flat prior that ranges from 0 to the maximum of line-of-sight as per the
    # SFD map, finally the excess noise parameters all have gaussian priors centered
    # around their respective uncertainties.
    #
    # Here, we know all CQVs are pre-main-sequence M-dwarfs.  So take broad
    # Teff and logg priors that use that knowledge.  They are _mostly_
    # close-by, so A_V should be small.  A_V=0.12 for the Pleiades
    # (Curtis2020), which is a high extinction sight-line.  So assume A_V<0.2. 
    f.prior_setup = {
            'teff': ('normal', 3000, 1000),
            'logg': ('normal', 4.5, 0.5),
            'z': ('uniform', -0.3, 0.3),
            'dist': ('default'),
            'rad': ('truncnorm', 0.5, 0.5, 0.1, 1.5),
            'Av': ('uniform', 0, 0.2)
    }

    cache_file = os.path.join(out_folder, 'BMA.pkl')

    if not os.path.exists(cache_file):
        f.initialize()
        # this takes like 10 minutes
        f.fit_bma()

    ##############
    # make plots #
    ##############
    out_folder = join(RESULTSDIR, 'ariadne_sed_fitting', f'{starname}')

    plots_out_folder = join(out_folder, 'plots')
    if not os.path.exists(plots_out_folder): os.mkdir(plots_out_folder)

    artist = SEDPlotter(cache_file, plots_out_folder, model='btsettl')
    artist.plot_SED_no_model()
    artist.plot_SED()
    artist.plot_bma_hist()
    artist.plot_bma_HR(10)
    artist.plot_corner()

    if (not pd.isnull(W3mag)):
        print(42*'-')
        print('Found WISE W3 and/or W4; making IR excess plot')
        plots_out_folder = join(out_folder, 'plots_irexcess')
        if not os.path.exists(plots_out_folder): os.mkdir(plots_out_folder)
        artist = SEDPlotter(cache_file, plots_out_folder, ir_excess=True, model='btsettl')
        artist.plot_SED_no_model()
        artist.plot_SED()

    print(f'Finished {ticid}')
    print(42*'-')
