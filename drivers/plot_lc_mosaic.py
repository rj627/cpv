import os
import complexrotators.plotting as rp
from complexrotators.paths import RESULTSDIR

PLOTDIR = os.path.join(RESULTSDIR, 'lc_mosaic')
if not os.path.exists(PLOTDIR):
    os.mkdir(PLOTDIR)

# NOTE: allchangers not implemented...
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_allchangers_3count',
                  showtitles=1, titlefontsize=3)
assert 0
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_allchangers_2count', showtitles=1)
#TODO

assert 0
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_changers')
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_changers', showtitles=1)
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_all')
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_all', showtitles=1)
rp.plot_lc_mosaic(PLOTDIR, subset_id='fav3')
rp.plot_lc_mosaic(PLOTDIR, subset_id='fav3', showtitles=1)
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_0')
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_0', showtitles=1)
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_1')
rp.plot_lc_mosaic(PLOTDIR, subset_id='dlt150_good_1', showtitles=1)
