#/usr/bin/env python
# File: steps_updated.py

#from start_nl import *
import numpy as np
import matplotlib.pyplot as plt
#from dna_diags import read_parameters, get_time_from_gout,read_time_step_g,get_grids
import os
import re
import multiprocessing as mp
import sys
import scipy.fft
import scipy.signal
from scipy.signal import find_peaks
from scipy.fft import fft,fftfreq,fftshift
import scipy.optimize as spo

par={}       #Global Variable to hold parameters once read_parameters is called
namelists={}

def read_parameters(lpath):
    """Reads parameters from parameters.dat \n
    The parameters are in a dictionary call par \n
    and can be accessed via par['parameter_name']"""
    if lpath==None:
        parfile=open('./parameters.dat','r')
    else:
        parfile=open(lpath+'/parameters.dat', 'r')
    parameters_in=parfile.read()
    lines=parameters_in.split('\n')
    #    parameters={}
    #note: par comes from config.py
    num_lines=len(lines)
    print( "Number of lines", num_lines)
    print(lines[0])
    for i in range(num_lines):
         temp=lines[i].split()
         if temp:
              str_check_namelist=re.match("&",temp[0])
         if str_check_namelist:
              current_namelist=temp[0]
              print(current_namelist)
              namelists[current_namelist]=" "
         if len(temp)>2:
              #if (re.match(\d):
              str_check_sn=re.match("\d*\.?\d*[eE]-?\+?\d*",temp[2])
              str_check_int=re.match("\d*",temp[2])
              str_check_float=re.match("\d*\.\d*",temp[2])
              if (str_check_sn and str_check_sn.end()==len(temp[2])):
                   par[temp[0]]=float(temp[2])
                   namelists[current_namelist]=namelists[current_namelist]+" "+temp[0]
              elif (str_check_float and str_check_float.end()==len(temp[2])):
                   par[temp[0]]=float(temp[2])
                   namelists[current_namelist]=namelists[current_namelist]+" "+temp[0]
              elif (str_check_int and str_check_int.end()==len(temp[2])):
                   float_temp=float(temp[2])
                   par[temp[0]]=int(float_temp)
                   namelists[current_namelist]=namelists[current_namelist]+" "+temp[0]
              else:
                   par[temp[0]]=temp[2]
                   namelists[current_namelist]=namelists[current_namelist]+" "+temp[0]

    #par['kxmax']=(par['nkx0']-1)*par['kxmin']
    #par['kymax']=(par['nky0']/2-1)*par['kymin']
    #par['kzmax']=(par['nkz0']/2-1)*par['kzmin']
    par['ky_nyq']=(par['nky0']//2)*par['kymin']
    par['kz_nyq']=(par['nkz0']//2)*par['kzmin']
    if par['etg_factor'] != 0.0:
        print( "!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print( "!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print( "Warning! field solver in dna diags not implement for ky=0 and etg_factor != 0.")
        print( "!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print( "!!!!!!!!!!!!!!!!!!!!!!!!!!")


def get_grids():
    """Returns kx,ky,kz grids in the same form as used in the code \n
    kxgrid = 0, kxmin, . . . kxmax \n
    kygrid = 0, kymin, . . . kymax, kymax+kymin, -kymax, . . . -kymin """
    kxgrid=np.arange((par['nkx0']))
    kxgrid=kxgrid*par['kxmin']
    kygrid=np.empty(par['nky0'])
    kzgrid=np.empty(par['nkz0'])
    herm_grid=np.arange(2)
    herm_grid=1.0*herm_grid
    for i in range(par['nky0']//2):
        kygrid[par['nky0']-1-i]=-float(i+1)*par['kymin']
        kygrid[i]=float(i)*par['kymin']
    kygrid[par['nky0']//2]=par['nky0']/2*par['kymin']
    for i in range(par['nkz0']//2):
        kzgrid[par['nkz0']-1-i]=-float(i+1)*par['kzmin']
        kzgrid[i]=float(i)*par['kzmin']
    kzgrid[par['nkz0']//2]=par['nkz0']//2*par['kzmin']
    return kxgrid,kygrid,kzgrid

def read_time_step_b(which_itime,swap_endian=False):
   """Reads a time step from b_out.dat.  Time step determined by \'which_itime\'"""
   file_name = par['diagdir'][1:-1]+'/b_out.dat'
   f = open(file_name,'rb')
   ntot=par['nkx0']*par['nky0']*par['nkz0']*3#par['nv0']
   mem_tot=ntot*16
   gt0=np.empty((3,par['nkz0'],par['nky0'],par['nkx0']))
   f.seek(8+which_itime*(8+mem_tot))
   gt0=np.fromfile(f,dtype='complex128',count=ntot)
   if swap_endian:
       gt0=gt0.newbyteorder()
   #print sum(gt0)
   f.close()
   return gt0

def read_time_step_v(which_itime,swap_endian=False):
   """Reads a time step from v_out.dat.  Time step determined by \'which_itime\'"""
   file_name = par['diagdir'][1:-1]+'/v_out.dat'
   f = open(file_name,'rb')
   ntot=par['nkx0']*par['nky0']*par['nkz0']*3#par['nv0']
   mem_tot=ntot*16
   gt0=np.empty((3,par['nkz0'],par['nky0'],par['nkx0']))
   f.seek(8+which_itime*(8+mem_tot))
   gt0=np.fromfile(f,dtype='complex128',count=ntot)
   if swap_endian:
       gt0=gt0.newbyteorder()
   #print sum(gt0)
   f.close()
   return gt0

def read_time_step_opt(which_itime,opt,swap_endian=False):
   """Reads a time step from opt_out.dat.  Time step determined by \'which_itime\'"""
   file_name = par['diagdir'][1:-1]+'/'+opt+'_out.dat'
   f = open(file_name,'rb')
   ntot=par['nkx0']*par['nky0']*par['nkz0']*3#par['nv0']                                                                                                                                                  
   mem_tot=ntot*16
   gt0=np.empty((3,par['nkz0'],par['nky0'],par['nkx0']))
   f.seek(4+which_itime*(4+mem_tot))
   gt0=np.fromfile(f,dtype='complex128',count=ntot)
   if swap_endian:
       gt0=gt0.newbyteorder()
   #print sum(gt0)                                                                                                                                                                                        
   f.close()
   return gt0

def read_time_step_energy(which_itime,ntp,swap_endian=False):
   """Reads a time step from opt_out.dat.  Time step determined by \'which_itime\'"""
   file_name = par['diagdir'][1:-1]+'/energy_out.dat'
   f = open(file_name,'rb')
   gt0=np.empty((1))
   ntot = 1 + ntp
   mem_tot = (ntot+2)*8
   gt0 = np.empty((ntp,1))
   f.seek(8+which_itime*(8+mem_tot))
   gt0=np.fromfile(f,dtype='float64',count=ntot)
   if swap_endian:
       gt0=gt0.newbyteorder()
   #print sum(gt0)                                                                                      \
   f.close()
   return gt0

def get_time_from_bout(swap_endian=False):
   """Returns time array taken from b_out.dat"""
   file_name = par['diagdir'][1:-1]+ '/b_out.dat'
   f = open(file_name,'rb')
   ntot=par['nkx0']*par['nky0']*par['nkz0']*3#par['nv0']
   mem_tot=ntot*16
   time=np.empty(0)
   continue_read=1
   i=0
   while (continue_read):
     f.seek(i*(mem_tot+8))
     i=i+1
     inp=np.fromfile(f,dtype='float64',count=1)
     if swap_endian:
         inp=inp.newbyteorder()
     #print inp
     if inp==0 or inp:
         time = np.append(time,inp)
     else:
         continue_read=0
   f.close()
   return time

def get_time_from_vout(swap_endian=False):
   """Returns time array taken from v_out.dat"""
   file_name = par['diagdir'][1:-1]+ '/v_out.dat'
   f = open(file_name,'rb')
   ntot=par['nkx0']*par['nky0']*par['nkz0']*3#par['nv0']
   mem_tot=ntot*16
   time=np.empty(0)
   continue_read=1
   i=0
   while (continue_read):
     f.seek(i*(mem_tot+8))
     i=i+1
     inp=np.fromfile(f,dtype='float64',count=1)
     if swap_endian:
         inp=inp.newbyteorder()
     #print inp
     if inp==0 or inp:
         time = np.append(time,inp)
     else:
         continue_read=0
   f.close()
   # print(time)
   # work = input('Proceed? Y/N ')
   # if work == 'N':
   #    quit('Wrong itimes')
   return time

def get_time_from_optout(opt,swap_endian=False):
   """Returns time array taken from v_out.dat"""
   file_name = par['diagdir'][1:-1]+ '/'+opt+'_out.dat'
   f = open(file_name,'rb')
   ntot=par['nkx0']*par['nky0']*par['nkz0']*3#par['nv0']                                                                                                                                                  
   mem_tot=ntot*16
   time=np.empty(0)
   continue_read=1
   i=0
   while (continue_read):
     f.seek(i*(mem_tot+4))
     i=i+1
     inp=np.fromfile(f,dtype='int32',count=1)
     if swap_endian:
         inp=inp.newbyteorder()
     #print inp                                                                                                                                                                                         
     if inp==0 or inp:
         time = np.append(time,inp)
     else:
         continue_read=0
   f.close()
   print(time)
   work = input('Proceed? Y/N ')
   if work == 'N':
       quit('Wrong itimes')
   return time

def get_time_from_energyout(ntp,swap_endian=False):
   """Returns time array taken from v_out.dat"""
   file_name = par['diagdir'][1:-1]+ '/energy_out.dat'
   f = open(file_name,'rb')
   ntot=1+ntp
   mem_tot=(ntot+2)*8
   time=np.empty(0)
   continue_read=1
   i=0
   while (continue_read):
     f.seek(i*(mem_tot+8))
     i=i+1
     inp=np.fromfile(f,dtype='float64',count=1)
     if swap_endian:
         inp=inp.newbyteorder()
     #print inp                                                                                  
     if inp==0 or inp:
         time = np.append(time,inp)
     else:
         continue_read=0
   print(time)
   work = input('Proceed? Y/N ')
   if work == 'N':
       quit('Wrong times')
   f.close()
   return time


def getb(lpath):
    """Saves b_out.dat (located in the directory specified by lpath) into a python-readable format b_xyz.dat
    which will also be located in the lpath directory.
    """
    #lpath='/scratch/04943/akshukla/hammet_dna_output/full/omt%g_nu%1.2f'%(omt,nu)
    #if lpath==None:
    #    lpath='/scratch/04943/akshukla/dna2mhd_output_0'
    read_parameters(lpath)
    time = get_time_from_bout()
    #time=time[:1000]
    kx,ky,kz=get_grids()
    i_n=[0,1,2]
    savepath = lpath+'/b_xyz.dat'
    #g=np.zeros((len(time)-1,len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64')
    #print('allocating array')
    g=np.memmap(savepath,dtype='complex64',mode='w+', shape=(len(time),len(kx),len(ky,),len(kz),len(i_n)) )
    np.save(lpath+'/bshape.npy',g.shape)
    np.save(lpath+'/timeb.npy',time)
    #g=np.zeros((len(time),len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64')
    #print('starting loop')
    print(par)
    print('time length = ', len(time))
    for t in range(len(time)):
        if(t%1000==0):
            print(str(t))
        gt = read_time_step_b(t)
        gt = np.reshape(gt,(par['nkx0'],par['nky0'],par['nkz0'],3),order='F')
        g[t] = gt
    #np.save(lpath+'/g_allk_g04',g)
    #print('finished loop')
    return time, g

def getv(lpath):
    """Saves v_out.dat (located in the directory specified by lpath) into a python-readable format v_xyz.dat
    which will also be located in the lpath directory.
    """
    #lpath='/scratch/04943/akshukla/hammet_dna_output/full/omt%g_nu%1.2f'%(omt,nu)
    #if lpath==None:
    #    lpath='/scratch/04943/akshukla/dna2mhd_output_0'
    read_parameters(lpath)
    time = get_time_from_vout()
    #time=time[:1000]
    kx,ky,kz=get_grids()
    i_n=[0,1,2]
    savepath = lpath+'/v_xyz.dat'
    #g=np.zeros((len(time)-1,len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64')
    #print('allocating array')
    g=np.memmap(savepath,dtype='complex64',mode='w+', shape=(len(time),len(kx),len(ky,),len(kz),len(i_n)) )
    np.save(lpath+'/vshape.npy',g.shape)
    np.save(lpath+'/timev.npy',time)
    #g=np.zeros((len(time),len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64')
    #print('starting loop')
    print(par)
    print('time length = ', len(time))
    for t in range(len(time)):
        if(t%1000==0):
            print(str(t))
        gt = read_time_step_v(t)
        gt = np.reshape(gt,(par['nkx0'],par['nky0'],par['nkz0'],3),order='F')
        g[t] = gt
    #np.save(lpath+'/g_allk_g04',g)
    #print('finished loop')
    return time, g

def getopt(lpath,opt):
    """Saves opt_out.dat (located in the directory specified by lpath) into a python-readable format opt_xyz.dat                                                                                              
    which will also be located in the lpath directory.                                                                                                                                                    
    """
    #lpath='/scratch/04943/akshukla/hammet_dna_output/full/omt%g_nu%1.2f'%(omt,nu)                                                                                                                        
    #if lpath==None:                                                                                                                                                                                      
    #    lpath='/scratch/04943/akshukla/dna2mhd_output_0'                                                                                                                                                 
    read_parameters(lpath)
    time = get_time_from_optout(opt)
    #time=time[:1000]                                                                                                                                                                                     
    kx,ky,kz=get_grids()
    i_n=[0,1,2]
    savepath = lpath+'/'+opt+'_xyz.dat'
    #g=np.zeros((len(time)-1,len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64')                                                                                                                       
    #print('allocating array')                                                                                                                                                                            
    g=np.memmap(savepath,dtype='complex64',mode='w+', shape=(len(time),len(kx),len(ky,),len(kz),len(i_n)) )
    np.save(lpath+'/'+opt+'shape.npy',g.shape)
    np.save(lpath+'/time'+opt+'.npy',time)
    #g=np.zeros((len(time),len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64')                                                                                                                         
    #print('starting loop')                                                                                                                                                                               
    print(par)
    print('time length = ', len(time))
    for t in range(len(time)):
        if(t%1000==0):
            print(str(t))
        gt = read_time_step_opt(t,opt)
        gt = np.reshape(gt,(par['nkx0'],par['nky0'],par['nkz0'],3),order='F')
        g[t] = gt
    #np.save(lpath+'/g_allk_g04',g)                                                                                                                                                                       
    #print('finished loop')
    f = open(lpath+'/dum'+opt+'.txt','w')
    f.write('Finished loop')
    f.close()
     
    return time, g

def getenergy(lpath,ntp):
    """Saves opt_out.dat (located in the directory specified by lpath) into a python-readable format opt_xyz.dat                                                                  which will also be located in the lpath directory."""
    #lpath='/scratch/04943/akshukla/hammet_dna_output/full/omt%g_nu%1.2f'%(omt,nu)                                                                                                #if lpath==None:                                                                                                                                                              #    lpath='/scratch/04943/akshukla/dna2mhd_output_0'                                                                                                                         read_parameters(lpath)
    
    time = get_time_from_energyout(ntp)
    #time=time[:1000] 

    kx,ky,kz=get_grids()
    i_n=[0,1,2]
    savepath = lpath+'/energy_xyz.dat'
    #g=np.zeros((len(time)-1,len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64') 
   #print('allocating array') 
    g=np.memmap(savepath,dtype='float64',mode='w+', shape=(len(time),ntp+1))
    np.save(lpath+'/energyshape.npy',g.shape)
    np.save(lpath+'/timeenergy.npy',time)
    #g=np.zeros((len(time),len(kx),len(ky,),len(kz),len(i_n)), dtype='complex64')
    #print('starting loop') 

    print(par)
    print('time length = ', len(time))
    for t in range(len(time)):
        if(t%20==0):
            print(str(t))
        gt = read_time_step_energy(t,ntp)
        gt = np.reshape(gt,(1+ntp),order='F')
        g[t] = gt
    #np.save(lpath+'/g_allk_g04',g)               

    #print('finished loop')

    f = open(lpath+'/dumen.txt','w')
    f.write('Finished loop')
    f.close()

    return time,g


def load_b(lpath):
    """
    This method can only be run after getb has been called at least once to save the b_xyz.dat file_name
    This quickly loads the b array which will have indices [time,kx,ky,kz, x/y/z]
    """
    read_parameters(lpath)
    if lpath==None:
        lpath='/scratch/04943/akshukla/dna2mhd_output_0'
    time = np.load(lpath+'/timeb.npy')
    bload=np.memmap(lpath+'/b_xyz.dat',dtype='complex64',mode='r',shape=tuple(np.load(lpath+'/bshape.npy')))
    return time, bload

def load_v(lpath):
    """
    This method can only be run after getv has been called at least once to save the v_xyz.dat file_name
    This quickly loads the v array which will have indices [time,kx,ky,kz, x/y/z]
    """
    read_parameters(lpath)
    if lpath==None:
        lpath='/scratch/04943/akshukla/dna2mhd_output_0'
    time = np.load(lpath+'/timev.npy')
    vload=np.memmap(lpath+'/v_xyz.dat',dtype='complex64',mode='r',shape=tuple(np.load(lpath+'/vshape.npy')))
    return time, vload

def load_opt(lpath,opt):
    """                                                                                                                                                                                                   
    This method can only be run after getv has been called at least once to save the v_xyz.dat file_name                                                                                                  
    This quickly loads the v array which will have indices [time,kx,ky,kz, x/y/z]                                                                                                                         
    """
    read_parameters(lpath)
    if lpath==None:
        lpath='/scratch/04943/akshukla/dna2mhd_output_0'
    time = np.load(lpath+'/time'+opt+'.npy')
    optload=np.memmap(lpath+'/'+opt+'_xyz.dat',dtype='complex64',mode='r',shape=tuple(np.load(lpath+'/'+opt+'shape.npy')))
    return time, optload

def load_energy(lpath):
    """  This method can only be run after getv has been called at least once to save the v_xyz.dat file_name    
    This quickly loads the v array which will have indices [time,kx,ky,kz, x/y/z]"""
    read_parameters(lpath)
    if lpath==None:
        lpath='/scratch/04943/akshukla/dna2mhd_output_0'
    time = np.load(lpath+'/timeenergy.npy')
    enload=np.memmap(lpath+'/energy_xyz.dat',dtype='float64',mode='r',shape=tuple(np.load(lpath+'/energyshape.npy')))
    return time, enload

def plot_bv(lpath,ix,iy,iz,ind,show=True):
    """
    This is an example method that plots the timetraces of b and v at the specified wavevector (kx[ix],ky[iy],kz[iz]).
    ind specifies whether you want the x(0),y(1), or z(2) component.
    """
    ind_strings= ['x','y','z']
    ind_string=ind_strings[ind]
    read_parameters(lpath)
    timeb,b=load_b(lpath)
    timev,v=load_v(lpath)
    fig,ax=plt.subplots(2)
    ax[0].plot(timeb,b[:,ix,iy,iz,ind].real,label='Re')
    ax[0].plot(timeb,b[:,ix,iy,iz,ind].imag,label='Im')
    ax[0].set_ylabel('b_%s'%ind_string)
    ax[0].set_xlabel('time')
    ax[1].plot(timev,v[:,ix,iy,iz,ind].real,label='Re')
    ax[1].plot(timev,v[:,ix,iy,iz,ind].imag,label='Im')
    ax[1].set_ylabel('v_%s'%ind_string)
    ax[0].set_xlabel('time')
    ax[0].legend()
    ax[1].legend()
    kx,ky,kz=get_grids()
    fig.suptitle('kx,ky,kz = %1.2f,%1.2f,%1.2f'%(kx[ix],ky[iy],kz[iz]))
    if lpath[-1] != '/':
        lpath = lpath + '/'
    if not os.path.exists(lpath + 'bvs/'):
        os.mkdir(lpath + 'bvs/')
    plt.savefig(lpath+'bvs/bv_%s_%d_%d_%d'%(ind_string,ix,iy,iz))
    if show == True:
        plt.show()
    dum = input('Log Zoom? Y/N ')
    if dum == 'Y':
        xl = int(input('Xmin? Integer '))
        xh = int(input('Xmax? Integer '))
        fig,ax=plt.subplots(2)
        ax[0].plot(timeb,b[:,ix,iy,iz,ind].real,label='Re')
        ax[0].plot(timeb,b[:,ix,iy,iz,ind].imag,label='Im')
        ax[0].set_ylabel('b_%s'%ind_string)
        ax[0].set_xlabel('time')
        ax[1].plot(timev,v[:,ix,iy,iz,ind].real,label='Re')
        ax[1].plot(timev,v[:,ix,iy,iz,ind].imag,label='Im')
        ax[1].set_ylabel('v_%s'%ind_string)
        ax[0].set_xlabel('time')
        ax[0].legend()
        ax[1].legend()       
        fig.suptitle('kx,ky,kz = %1.2f,%1.2f,%1.2f'%(kx[ix],ky[iy],kz[iz]))
        ax[0].set_xlim(xl,xh)
        ax[1].set_xlim(xl,xh)
        ax[0].set_ylim(0.01,10**8)
        ax[0].set_yscale('log')
        ax[1].set_ylim(0.01,10**8)
        ax[1].set_yscale('log')
        plt.yscale('log')
        plt.savefig(lpath+'bvs/zoomed_bv_%s_%d_%d_%d'%(ind_string,ix,iy,iz))
        plt.show()
    plt.close()
    return timeb,b,timev,v


def plot_vreal_spectrum(lpath,ix,iy,iz,ind):
    """
    ix,iy,iz specifies the wavevector
    ind specifies x/y/z (0/1/2) component
    This is an example method that performs the fft on the real part of v and plots the result.
    It will return an array of the frequencies found.
    *** Right now it seems like freqs need to multiplied by 2*pi to get the right dispersion relation.
        I think this makes sense because w = 2*pi*f
    """
    ind_strings= ['x','y','z']
    ind_string=ind_strings[ind]
    read_parameters(lpath)
    time,v=load_v(lpath)
    v_k = v[:,ix,iy,iz,ind]
    #plt.plot(time,v_k)
    #plt.show()
    sp=fftshift(fft(v_k-np.mean(v_k.real)))
    freq = fftshift(fftfreq(time.shape[-1],d=.01))
    peaks,_ = find_peaks(np.abs(sp),threshold=10)
    print(freq[peaks])
    print(freq[peaks]*2*np.pi)
    plt.plot(np.abs(sp))
    plt.plot(peaks, sp[peaks], "x")
    plt.show()
    return 2*np.pi*freq[peaks]

def plot_vspectrum(lpath,ix,iy,iz,ind):
    """
    ix,iy,iz specifies the wavevector
    ind specifies x/y/z (0/1/2) component
    This is an example method that performs the fft on the real part of v and plots the result.
    It will return an array of the frequencies found.
    *** Right now it seems like freqs need to multiplied by 2*pi to get the right dispersion relation.
        I think this makes sense because w = 2*pi*f
    """
    ind_strings= ['x','y','z']
    ind_string=ind_strings[ind]
    read_parameters(lpath)
    kx,ky,kz=get_grids()
    time,v=load_v(lpath)
    v_k = v[:,ix,iy,iz,ind]
    #plt.plot(time,v_k)
    #plt.show()
    sp=fftshift(fft(v_k-np.mean(v_k)))
    freq = fftshift(fftfreq(time.shape[-1],d=.01))
    omega = 2*np.pi*freq
    peaks,_ = find_peaks(np.abs(sp),threshold=10)
    print(freq[peaks])
    print(freq[peaks]*2*np.pi)
    omega_plot = omega[(omega>-2*np.pi)&(omega<2*np.pi)]
    sp_plot= sp[(omega>-2*np.pi)&(omega<2*np.pi)]
    plt.plot(omega_plot, np.abs(sp_plot))
    #plt.plot(peaks, sp[peaks], "x")
    plt.ylabel('|FFT(v_%s)|'%ind_string )
    plt.xlabel('frequency')
    plt.title('kx,ky,kz = %1.2f,%1.2f,%1.2f'%(kx[ix],ky[iy],kz[iz]))
    if lpath[-1] != '/':
        lpath =lpath +'/'
    if not os.path.exists(lpath + 'vspectra/'):
        os.mkdir(lpath + 'vspectra/')
    plt.savefig(lpath+'vspectra/vspectrum_%s_%d_%d_%d'%(ind_string,ix,iy,iz))
    if show == True:
        plt.show()
    plt.close()
    return omega[peaks]

def plot_nls(lpath,ix,iy,iz,ind,show=True):
    """This an example method that plots the timetraces of b and v at the specified wavevector (kx[ix],ky[iy],kz[iz]).
ind specifies whether you want the x(0),y(1), or z(2) component."""
    ind_strings= ['x','y','z']
    ind_string=ind_strings[ind]
    read_parameters(lpath)
    opts = ['bdv','vdb','bdcb','cbdb','vdv','bdb','db2']
    fmts = {'bdv':'-m','vdb':'^m','bdcb':'--k','cbdb':'2k','vdv':'Hr',
        'bdb':':b','db2':'sb'}
 
    fig,ax = plt.subplots(2)
    i = 0

    optlist = []
    for opt in opts:
        if os.path.isfile(lpath+'/dum'+opt+'.txt'):
            optlist.append(load_opt(lpath,opt))
        else:
            optlist.append(getopt(lpath,opt))
        t = optlist[i][0]
        opty = np.array(optlist[i][1][:,ix,iy,iz,ind])
        ax[0].plot(t,opty.real,fmts[opt],markersize=1,label=opt)
        ax[1].plot(t,opty.imag,fmts[opt],markersize=1,label=opt)
        i = i + 1

    ax[0].set_ylabel('real nonlinearity %s'%ind_string)
    ax[0].set_xlabel('time')
    ax[1].set_ylabel('imag nonlinearity %s'%ind_string)
    ax[0].set_xlabel('time')
    ax[0].legend()
    ax[1].legend()
    ax[0].set_ylabel('real nonlinearity %s'%ind_string)
    ax[0].set_xlabel('time')
    ax[1].set_ylabel('imag nonlinearity %s'%ind_string)
    ax[1].set_xlabel('time')
    ax[0].legend()
    ax[1].legend()

    kx,ky,kz=get_grids()
    fig.suptitle('kx,ky,kz = %1.2f,%1.2f,%1.2f'%(kx[ix],ky[iy],kz[iz]))

    if lpath[-1] != '/':
        lpath = lpath + '/'
    if not os.path.exists(lpath + 'nls/'):
        os.mkdir(lpath + 'nls/')
    plt.savefig(lpath+'nls/nls_%s_%d_%d_%d'%(ind_string,ix,iy,iz))
    if show == True:
        plt.show()
    plt.close()

    duml = input('Log Zoom? Y/N ')
    if duml == 'Y':
        xl = int(input('Xmin? Integer '))
        xh = int(input('Xmax? Integer '))
        fig,ax = plt.subplots(2)
        i = 0
        for opt in opts:
            t = optlist[i][0]
            opty = np.array(optlist[i][1][(t>xl)*(t<xh),ix,iy,iz,ind])
            t = np.array(t[(t>xl)*(t<xh)])
            ax[0].plot(t,opty.real,fmts[opt],markersize=1,label=opt)
            ax[1].plot(t,opty.imag,fmts[opt],markersize=1,label=opt)
            i = i + 1
        ax[0].set_ylabel('real nonlinearity %s'%ind_string)
        ax[0].set_xlabel('time')
        ax[1].set_ylabel('imag nonlinearity %s'%ind_string)
        ax[0].set_xlabel('time')
        ax[0].legend()
        ax[1].legend()
        ax[0].set_ylabel('real nonlinearity %s'%ind_string)
        ax[0].set_xlabel('time')
        ax[1].set_ylabel('imag nonlinearity %s'%ind_string)
        ax[1].set_xlabel('time')
        ax[0].legend()
        ax[1].legend()
        ax[0].set_ylim(.01,10**8)
        ax[1].set_ylim(.01,10**8)
        ax[0].set_yscale('log')
        ax[1].set_yscale('log')
        fig.suptitle('kx,ky,kz = %1.2f,%1.2f,%1.2f'%(kx[ix],ky[iy],kz[iz]))
        plt.savefig(lpath+'nls/nllogs_%s_%d_%d_%d'%(ind_string,ix,iy,iz))
        if show == True:
            plt.show()
        plt.close()

    dum = input('Bar Zoom? Y/N ')
    if dum == 'Y':
        Nb = 4
        N = 4*par['max_itime']
        bottom = np.zeros(Nb)
        upbottom = np.ones(Nb)
        lowbottom = -1*np.ones(Nb)
        cs = {'bdv':'m','vdb':'m','bdcb':'k','cbdb':'k','vdv':'r',
            'bdb':'b','db2':'b'}
        hatchs = {'bdv':'+','vdb':'0','bdcb':'\\','cbdb':'/','vdv':'*','bdb':'x','db2':'.'}

        xl = int(input('Xmin? Integer '))
        xh = int(input('Xmax? Integer '))
        x =  np.linspace(xl+(xh-xl)/(2*Nb),xh-(xh-xl)/(2*Nb),num=Nb)
        fig,ax=plt.subplots(2)
        i = 0 

        for opt in opts:
            y = np.zeros(Nb)
            t = optlist[i][0]
            opty = np.array(optlist[i][1][(t>xl)*(t<xh),ix,iy,iz,ind])
            t = np.array(t[(t>xl)*(t<xh)]) 
            N = np.size(t)
            for j in range(0,np.size(t),4):
                opty[j] = opty[j] * .01/6
                opty[j+1] = opty[j] * 2*.01/6
                opty[j+2] = opty[j] * 2*.01/6
                opty[j+3] = opty[j] * .01/6
            w = 2/3*(xh-xl)/(Nb)
            for j in range(Nb):
                y[j] = np.sum(opty[j*(N//Nb):(j+1)*(N//Nb)],dtype='complex64')
                if y[j] >= 0:
                    bottom[j] = upbottom[j]
                if y[j] < 0:
                    bottom[j] = lowbottom[j]
            y0 = y.real.astype('int')
            y1 = y.imag.astype('int')
            ax[0].bar(x,y0,width=w,color=cs[opt],hatch=hatchs[opt],label=opt,bottom=bottom,align='center')        
            ax[1].bar(x,y1,width=w,color=cs[opt],hatch=hatchs[opt],label=opt,bottom=bottom,align='center')
            
            print(y0,y1)
            for j in range(Nb):
                if (j%10000) == 0:
                    print(j)
                if y[j] >= 0:
                    upbottom[j] += y[j]
                if y[j] < 0:
                    lowbottom[j] += y[j]
            i = i + 1

        ax[0].set_ylabel('real + nonlinearity')
        ax[0].set_xlabel('itime')
        ax[1].set_ylabel('real - nonlinearity')
        ax[0].set_xlabel('itime')
        ax[0].legend()
        ax[1].legend()
        fig.suptitle('kx,ky,kz = %1.2f,%1.2f,%1.2f'%(kx[ix],ky[iy],kz[iz]))
        ax[0].set_xlim(xl,xh)
        ax[1].set_xlim(xl,xh)
        #ax[0].set_ylim(0.01,10**8)
        #ax[0].set_yscale('log')
        #ax[1].set_ylim(-10**8,-0.01)
        #ax[1].set_yscale('log')
        plt.savefig(lpath+'nls/logbar_nls_%s_%d_%d_%d'%(ind_string,ix,iy,iz))
        plt.show()
        plt.close()

    return 0

def plot_energy(lpath,ntp,show=True):
    """ Plots Scalars Written in energy_out.dat """

    read_parameters(lpath)
    if os.path.isfile(lpath+'/dumen.txt'):
        timeen,enval = load_energy(lpath)
    else:
        timeen,enval = getenergy(lpath,ntp)

    shapes = {1:(1,1),2:(2,1),3:(2,2),4:(2,2),5:(2,3),6:(2,3),7:(3,3),8:(3,3),9:(3,3)}
    s = shapes[ntp+1]
    labels = {0:'Energy',1:'Magnetic Helicity',2:'Cross Helicity',3:'Entropy',4:'Next Param',5:'Next Param',6:'Next Param',7:'Next Param',8:'Next Param'}
    fnames = {0:'energy',1:'maghcty',2:'crosshcty',3:'entropy',4:'par4',5:'par5',6:'par6',7:'par7',8:'par8'}
    
    if not os.path.exists(lpath + '/eplots/'):
        os.mkdir(lpath + '/eplots/')
       
    for i in range(ntp+1):
        fig,ax = plt.subplots(1)
        ax.plot(timeen,enval[:,i])
        ax.set_xlabel('time')
        ax.set_ylabel(labels[i])
        fig.suptitle(labels[i])
        plt.savefig(lpath+'/eplots/'+fnames[i])
        if np.amax(enval) > 10 ** 5:
            ax.set_ylim(0,10**5)
        if show == True:
            plt.show()
        plt.close()
    
    return timeen,enval


#if __name__ == '__main__':
#    #count = mp.cpu_count()
#    #start = 1
#    #stop = start+count
#    params = [(12,0.05), (15,0.20), (15,0.50), (5,0.00), (6, 0.00), (6,0.01), (6,0.05), (6,0.10), (6,0.50), (7,0.00), (7,0.01), (7,0.05), (7,0.50), (8,0.00), (8,0.01), (8,0.10), (8,0.50), (9,0.00), (9,0.01), (9,0.20), (9,0.50)]
#    count = len(params)
#    print('params = ', params)
#    print('count = %d'%count)
#    p = mp.Pool(count)
#    p.starmap(saveg,params)
#    #scores = p.map(gbmerror, range(start, stop))
#    #scores = np.array(scores)
#    #np.save('scores', scores)
#    p.close()
#    p.join()
#    print('all done')


#iif __name__ == '__main__':
#    omt = int(sys.argv[1])
#    nu = float(sys.argv[2])
#    style = str(sys.argv[3])
#    print(omt,nu, style)
#    print(type(omt), type(nu))
#    saveg(omt,nu,style)
#

def analytical_omega(lpath,ix,iy,iz):
    read_parameters(lpath)
    kx,ky,kz = get_grids()
    wp = kz[iz]*(np.sqrt(kx[ix]**2+ky[iy]**2+kz[iz]**2)/2 + np.sqrt(1+ (kx[ix]**2+ky[iy]**2+kz[iz]**2)/4))
    wm = kz[iz]*(np.sqrt(kx[ix]**2+ky[iy]**2+kz[iz]**2)/2 - np.sqrt(1+ (kx[ix]**2+ky[iy]**2+kz[iz]**2)/4))
    return wp,wm

def fit_cexpr(t,A,r,w):
    return A * np.exp(r*t) * np.cos(w*t)

def fit_cexpi(t,A,r,w):
    return A * np.exp(r*t) * np.sin(w*t)

def growth_rate(t,y):
    t = np.array(t)
    y = np.reshape(y,np.size(y))
    poptr,pcov = spo.curve_fit(fit_cexpr,t,y.real,p0=[10**3,.01,.6])
    popti,pcov = spo.curve_fit(fit_cexpi,t,y.imag,p0=[10**3,.01,.6])
    return (poptr[1],poptr[2], popti[1],popti[2])
