"""
Contents:

| get_2min_cadence_spoc_tess_lightcurve
| get_20sec_cadence_spoc_tess_lightcurve
| _get_lcpaths_given_ticid
| _get_local_lcpaths_given_ticid
| _get_lcpaths_fromlightkurve_given_ticid

| get_cqv_search_sample

tic4029 specialized:
| get_tic4029_lc_and_mask
| get_4029_manual_mask

"""
import numpy as np, pandas as pd
import lightkurve as lk
from os.path import join
from glob import glob
import subprocess
from complexrotators.paths import LKCACHEDIR, LOCALDIR, RESULTSDIR

def get_cqv_search_sample():
    localdir = '/Users/luke/local/SPOCLC'
    csvpath = join(localdir, 'gaia_X_spoc2min_merge.csv')
    df = pd.read_csv(csvpath)

    sel = (
        (df.TESSMAG < 16) & (df.bp_rp > 1.5) &
        (df.M_G > 4) & (df.parallax > 1e3*(1/150)) &
        (df.SECTOR <= 55)
    )

    sdf = df[sel]
    return sdf


def get_tic4029_lc_and_mask(model_id):
    """
    model_id, e.g., 'manual_20230617_mask_v0_nterms2'
    """

    from complexrotators.lcprocessing import prepare_cpv_light_curve

    ticid = '402980664'
    sample_id = '2023catalog_LGB_RJ_concat' # used for cacheing
    cachedir = join(LOCALDIR, "cpv_finding", sample_id)

    lcpaths = _get_lcpaths_fromlightkurve_given_ticid(ticid)

    # stack over all sectors
    times, fluxs, cadencenos = [], [], []
    for lcpath in np.sort(lcpaths):
        (time, flux, qual, x_obs, y_obs, y_flat, y_trend, x_trend, cadence_sec,
         sector, starid, cadenceno) = prepare_cpv_light_curve(
             lcpath, cachedir, returncadenceno=1
         )
        times.append(x_obs)
        fluxs.append(y_flat)
        cadencenos.append(cadenceno)
    times = np.hstack(np.array(times, dtype=object).flatten())
    fluxs = np.hstack(np.array(fluxs, dtype=object).flatten())
    cadencenos = np.hstack(np.array(cadencenos, dtype=object).flatten())

    if 'manual_20230617_mask_v0' in model_id:
        full_ood = get_4029_manual_mask(times, fluxs, cadencenos, get_full=1)

    return times, fluxs, full_ood


def get_4029_manual_mask(times, fluxs, cadencenos, get_full=0):

    # made using glue, with the manual_masking_20230617.glu session
    maskpaths = np.sort(
        glob(join(RESULTSDIR, 'tic4029_segments', '*manual_mask*.csv'))
    )

    # out of dip times, fluxs, cadenceno's
    ood_df = pd.concat((pd.read_csv(m) for m in maskpaths))
    ood_df = ood_df.sort_values(by='cadenceno')

    # full out of dip mask
    full_ood = np.in1d(cadencenos, np.array(ood_df.cadenceno))

    # sectors 18 and 19 out of dip
    s18s19_ood = full_ood & (times > 1750) & (times < 1900)

    # sectors 25 and 26 out of dip
    s25s26_ood = full_ood & (times > 1950) & (times < 2100)

    # sectors 53, 58, 59 out of dip
    s53s58s59_ood =  full_ood & (times > 2600)

    if get_full:
        return full_ood

    if get_split:
        return s18s19_ood, s25s26_ood, s53s58s59_ood, full_ood



def _get_lcpaths_given_ticid(ticid):
    # TODO: this getter will need to be updated when running at scale on wh1
    SPOCDIR = "/Users/luke/local/SPOCLC"
    lcpaths = glob(join(SPOCDIR, "lightcurves", f"*{ticid}*.fits"))

    if len(lcpaths) == 0:
        p = subprocess.call([
            "scp", f"luke@wh1:/ar1/TESS/SPOCLC/sector*/*{ticid}*.fits",
            join(SPOCDIR, "lightcurves")
        ])
        assert 0
    return lcpaths


def _get_lcpaths_fromlightkurve_given_ticid(ticid, require_lc=1):
    # ticid like "289840928"

    assert isinstance(ticid, str)
    if ticid.startswith("TIC"):
        ticid_str = ticid
    else:
        ticid_str = f"TIC {ticid}"

    lcset = lk.search_lightcurve(ticid_str)

    sel = (lcset.author=='SPOC') & (lcset.exptime.value == 120)
    lcc = lcset[sel].download_all()

    lcpaths = glob(
        join(LKCACHEDIR, f'tess*{ticid}*-s', f'tess*{ticid}*-s_lc.fits')
    )

    if require_lc:
        msg = f'{ticid}: did not get LC'
        assert len(lcpaths) > 0, msg

    return lcpaths


def _get_local_lcpaths_given_ticid(ticid):

    from complexrotators.paths import SPOCDIR

    lcpaths = glob(join(SPOCDIR, "sector-*", f"*{ticid}*.fits"))

    if len(lcpaths) == 0:
        print(f"Failed to find 2 minute light curves for {ticid}")

    return lcpaths


def get_2min_cadence_spoc_tess_lightcurve(
    ticstr: str,
    ) -> list:
    """
    Args:
        ticstr: e.g., 'TIC 441420236'.  will be passed to lightkurve and used
        in naming plots.

    Returns:
        list containing individual sector-by-sector light curves.  If none are
        found, an empty list is returned.
    """

    # get the light curve
    lcset = lk.search_lightcurve(ticstr)

    if len(lcset) == 0:
        return []

    sel = (lcset.author=='SPOC') & (lcset.exptime.value == 120)
    lcc = lcset[sel].download_all()

    if lcc is None:
        return []

    # select only the two-minute cadence SPOC-reduced data; convert to a list.
    # note that this conversion approach works for any LightCurveCollection
    # returned by lightkurve -- no need to hand-pick the right ones.  the exact
    # condition below says "if the interval is between 119 and 121 seconds,
    # take it".
    lc_list = [_l for _l in lcc
         if
         _l.meta['ORIGIN']=='NASA/Ames'
         and
         np.isclose(
             120,
             np.nanmedian(np.diff(_l.remove_outliers().time.value))*24*60*60,
             atol=5
         )
    ]

    return lc_list


def get_20sec_cadence_spoc_tess_lightcurve(
    ticstr: str,
    ) -> list:
    """
    Args:
        ticstr: e.g., 'TIC 441420236'.  will be passed to lightkurve and used
        in naming plots.

    Returns:
        list containing individual sector-by-sector light curves.  If none are
        found, an empty list is returned.
    """

    # get the light curve
    lcset = lk.search_lightcurve(ticstr)

    if len(lcset) == 0:
        return []

    sel = (lcset.author=='SPOC') & (lcset.exptime.value == 20)
    lcc = lcset[sel].download_all()

    if lcc is None:
        return []

    # select only the two-minute cadence SPOC-reduced data; convert to a list.
    # note that this conversion approach works for any LightCurveCollection
    # returned by lightkurve -- no need to hand-pick the right ones.  the exact
    # condition below says "if the interval is between 119 and 121 seconds,
    # take it".
    lc_list = [_l for _l in lcc
         if
         _l.meta['ORIGIN']=='NASA/Ames'
         and
         np.isclose(
             20,
             np.nanmedian(np.diff(_l.remove_outliers().time.value))*24*60*60,
             atol=5
         )
    ]

    return lc_list
