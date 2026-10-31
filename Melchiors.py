import numpy as np
import astropy.io.fits as pf

spectrum = 'EstrellaProblema1.dat'

### We read the header, where we can find info about the target (name, coordinates...) and the observations (date, exposure time, sky conditions...) ###
headerc = pf.getheader(spectrum)
starname = headerc['Problema1'] 

### We read the data ###
specc = pf.getdata(spectrum)
wave = specc['wave']
flux = specc['flux_norm'] #If you want it NORMALIZED
#flux = specc['flux_tac'] #If you want it NOT normalized

### We save wavelength and flux in a 2-column .dat file with the same original name ###
np.savetxt(spectrum[:-5]+'.dat', np.array([wave, flux]).T, fmt='%f', delimiter='\t')

