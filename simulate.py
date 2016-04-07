import subprocess
import datetime
from multiprocessing import Pool, Process, Queue
import os
import tempfile
import numpy as np
from sensing.methods import *
from sensing.signals import *
import sys
import progressbar
import itertools
import traceback
from optparse import OptionParser

OUTPATH=datetime.datetime.now().strftime("simout-%Y%m%d-%H%M%S")

Np = 1000

def get_path(genc, func, funcname, Ns, fs, Pgen):
	mp_slug = "sim"

	if Pgen is None:
		suf = 'off.dat'
	else:
		m = '%.1f' % (Pgen,)
		m = m.replace('-','m')
		m = m.replace('.','_')

		suf = '%sdbm.dat' % (m,)

	path = '%s/dat/%s_%s_fs%dmhz_Ns%dks_' % (
				OUTPATH,
				mp_slug,
				genc.SLUG, fs/1e6, Ns/1000)
	path += '%s_' % (func.SLUG,)
	if funcname:
		path += funcname + "_"

	path += suf

	return path

def run_simulation(genc, det, Np, Ns, fc, fs, Pgen):

	N = Np*Ns

	x = genc.get(N, fc, fs, Pgen)
	assert len(x) == N

	jl = range(0, N, Ns)
	assert len(jl) == Np

	gammal = np.empty(shape=Np)
	for func, funcname in det:

		for i, j in enumerate(jl):
			x0 = x[j:j+Ns]
			gammal[i] = func(x0)

		path = get_path(genc, func, funcname, Ns, fs, Pgen)

		assert not os.path.exists(path)
		np.savetxt(path, gammal)

def run_simulation_(kwargs):
	try:
		return run_simulation(**kwargs)
	except Exception:
		traceback.print_exc()
		raise

def make_campaign_det_gencl(fc, det, fsNsl, gencl, Pgenl):
	task_list = []
	for Pgen in Pgenl:
		for fs, Ns in fsNsl:
			for genc in gencl:
				task_list.append({
					'genc': genc,
					'det': det,
					'Np': Np,
					'Ns': Ns,
					'fc': fc,
					'fs': fs,
					'Pgen': Pgen
				})

	return task_list

def make_sampling_campaign_gencl(fsNsl, gencl, Pgenl):

	fc = 864e6

	det = [	(EnergyDetector(), None) ]

	cls = [	CAVDetector,
		CFNDetector,
		MACDetector,
		MMEDetector,
		EMEDetector,
		AGMDetector,
		METDetector ]

	#for L in xrange(5, 25, 5):
	#	for c in cls:
	#		det.append((c(L=L), "l%d" % (L,)))

	for scfNp in [64, 128]:
		det += [ (SCFDetector(Np=scfNp, L=scfNp/4), "Np%d" % (scfNp,)) ]

	return make_campaign_det_gencl(fc, det, fsNsl, gencl, Pgenl)

def make_sneismtv_campaign_gencl(fsNsl, gencl, Pgenl):

	fc = 850e6

	Ns_list = [ 3676, 1838, 1471 ]

	det = []
	for Ns in Ns_list:
		det.append((SNEISMTVDetector(N=Ns), "n%d" % (Ns,)))

	return make_campaign_det_gencl(fc, det, fsNsl, gencl, Pgenl)

def ex_sim_spurious_campaign_mic():

	fsNs = [ (2e6, 25000) ]
	Pgenl = [None] + range(-140, -100, 1)

	fnl = [
		3.*fs/8.,
		3.*fs/8.+1e3,
#		fs/4.,
#		fs/4.+1e3,
#		fs/8.,
#		fs/8.+1e3,
#		fs/32.,
#		fs/128.,
	]

	gencl = []
#	gencl.append(SimulatedIEEEMicSoftSpeaker())

	Pnl  = range(-130, -100, 2)
	for Pn in Pnl:
		for fn in fnl:
			gencl.append(AddSpuriousCosine(SimulatedIEEEMicSoftSpeaker(), fn, Pn=Pn))

	return make_sampling_campaign_gencl(fsNs, gencl, Pgenl)

def ex_sim_gaussian_noise_campaign_mic():

	fsNs = [ (2e6, 25000) ]
	Pgenl = [None] + range(-140, -100, 1)

	gencl = []
	gencl.append(SimulatedIEEEMicSoftSpeaker())

	Pnl  = range(-130, -100, 2)
	for Pn in Pnl:
		gencl.append(AddGaussianNoise(SimulatedIEEEMicSoftSpeaker(), Pn=Pn))

	return make_sampling_campaign_gencl(fsNs, gencl, Pgenl)


def ex_sim_oversample_campaign_mic():

	fsNs = [ (2e6, 25000) ]
	Pgenl = [None] + range(-140, -100, 1)

	#kl = range(1, 9)
	kl = [1]

	gencl = []
	for k in kl:
		gencl.append(Divide(Oversample(SimulatedIEEEMicSoftSpeaker(), k=k), Nb=Ns*4))

	return make_sampling_campaign_gencl(fsNs, gencl, Pgenl)

def ex_sim_campaign_mic():

	fsNs = [	(1e6, 25000),
			(2e6, 25000),
			(10e6, 100000),
		]
	Pgenl = [None] + range(-140, -100, 1)

	gencl = []
	gencl.append(AddGaussianNoise(SimulatedIEEEMicSoftSpeaker(), Pn=-100))

	return make_sampling_campaign_gencl(fsNs, gencl, Pgenl)

def ex_calc_campaign_mic():

	fsNs = [	(1e6, 25000),
			(2e6, 25000),
			(10e6, 100000),
		]
	Pgenl = [None] + range(-100, -70, 1)

	gencl = [ LoadMeasurement("samples/usrp_micsoft_fs%(fs)smhz_Ns%(Ns)sks_%(Pgen)s.npy", Np=Np) ]

	return make_sampling_campaign_gencl(fsNs, gencl, Pgenl)

def ex_calc_sneismtv_campaign_mic():

	fsNs = [	(0, 3676),
		]

	Pgenl = [None] + range(-100, -70, 1)

	gencl = [ LoadMeasurement("samples-sneismtv_campaign_mic/sneismtv_micsoft_fs%(fs)smhz_Ns%(Ns)sks_%(Pgen)s.npy", Np=Np) ]

	return make_sneismtv_campaign_gencl(fsNs, gencl, Pgenl)

def ex_sim_campaign_noise():

	fsNs = [	(1e6, 25000),
			(2e6, 25000),
			(10e6, 100000),
		]
	Pgenl = range(-100, -60, 1)


	gencl = []
	gencl.append(SimulatedNoise())

	return make_sampling_campaign_gencl(fsNs, gencl, Pgenl)

def ex_calc_campaign_noise():

	fsNs = [	(1e6, 25000),
			(2e6, 25000),
			(10e6, 100000),
		]
	Pgenl = [None] + range(-70, -10, 2)

	gencl = [ LoadMeasurement("samples-usrp_campaign_noise/usrp_noise_fs%(fs)smhz_Ns%(Ns)sks_%(Pgen)s.npy", Np=Np) ]

	return make_sim_campaign_gencl(fsNs, gencl, Pgenl)

def ex_calc_sneshtercov_campaign_unb():

	fsNs = [	(2e6, 20) ]

	fc = 700e6

	det = [	(EnergyDetector(), None) ]

	cls = [	SNEESHTERCAVDetector,
		SNEESHTERMACDetector ]

	for L in xrange(5, 25, 5):
		for c in cls:
			det.append((c(L=L), "l%d" % (L,)))

	gencl = [ LoadMeasurement("samples-eshtercov/eshtercov_unb_fs%(fs)smhz_Ns%(Ns)sks_%(Pgen)s.npy", Np=Np) ]

	Pgenl = [None] + range(-100, -85, 1)

	return make_campaign_det_gencl(fc, det, fsNs, gencl, Pgenl)

def cmdline():
	parser = OptionParser()
	parser.add_option("-f", dest="func", metavar="FUNCTION",
			help="function to run")
	parser.add_option("-o", dest="outpath", metavar="PATH",
			help="output directory")
	parser.add_option("-p", dest="nproc", metavar="NPROC", type="int", default=4,
			help="number of processes to run")
	parser.add_option("-s", dest="slice", metavar="SLICE", default="0:1",
			help="slice of tasklist to run (e.g. 1:10 for slice 1 of 10)")

	(options, args) = parser.parse_args()

	return options

def make_slice(task_list, options):
	i, n = map(int, options.slice.split(":"))

	#print "slice %d of %d" % (i, n)

	m = len(task_list)

	#print "task list len", m

	slice_size = m/n
	if m % n > 0:
		slice_size += 1

	#print "slice size", slice_size

	start = slice_size*i

	#print "from %d to %d" % (start, start+slice_size)

	assert(slice_size*n >= m)

	return task_list[start:start+slice_size]

def run(task_list, options):
	pool = Pool(processes=options.nproc)

	task_list = make_slice(task_list, options)
	if not task_list:
		return

	widgets = [ progressbar.Percentage(), ' ', progressbar.Bar(), ' ', progressbar.ETA() ] 
	pbar = progressbar.ProgressBar(widgets=widgets, maxval=len(task_list))
	pbar.start()

	for i, v in enumerate(pool.imap_unordered(run_simulation_, task_list)):
	#for i, v in enumerate(itertools.imap(run_simulation_, task_list)):
		pbar.update(i)

	pbar.finish()
	print

	#run_simulation_(task_list[0])

def main():
	global OUTPATH

	options = cmdline()

	if options.func is not None:

		if options.outpath:
			OUTPATH = options.outpath

		try:
			os.mkdir(OUTPATH)
			os.mkdir(OUTPATH + "/dat")
		except OSError:
			pass

		f = open(OUTPATH + "/args", "w")
		f.write(' '.join(sys.argv) + '\n')
		f.close()

		task_list = globals()[options.func]()
		run(task_list, options)

		open(OUTPATH + "/done", "w")
	else:
		print "Specify function to run with -f"
		print
		print "available functions:"
		funcs = []
		for name, val in globals().iteritems():
			if not callable(val):
				continue
			if name.startswith("ex_"):
				funcs.append(name)

		funcs.sort()

		for name in funcs:
			print "   ", name

if __name__ == "__main__":
	main()
