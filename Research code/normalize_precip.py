#!/usr/bin/env python
# coding: utf-8

# In[4]:


import xarray as xr
import numpy as np
from global_land_mask import globe
import sys
import glob
import json


# In[2]:


#Lazy loading in evaporation data
EVAP_DATA = xr.open_dataset('/glade/derecho/scratch/considine/ERA5/evap.nc')

#Selecting time slice
EVAP_DATA = EVAP_DATA.sel(valid_time=slice('2011','2016'))

#Multiplying by -1000 to get proper units and sign
EVAP_DATA *= -1000

#Filtering out negative values
EVAP_DATA['e'] = EVAP_DATA['e'].where(EVAP_DATA['e'] >= 0, 0)

#Shifting longitude coordinates to be from -180 to 180
EVAP_DATA['longitude'] = (EVAP_DATA['longitude']+180)%360 - 180
EVAP_DATA = EVAP_DATA.sortby("longitude")

#Loading data into memory
EVAP_DATA = EVAP_DATA.load()


# In[3]:


#Function takes a range of latitude and longitude as inputs and returns the surface area in that range
def calculate_area(latRange,lonRange):

    lat = np.radians(latRange)
    lon = np.radians(lonRange)

    #Radius of the earth in meters
    R = 6371000 

    Area = (R**2)*(np.abs(np.sin(lat[1])-np.sin(lat[0])))*(np.abs(lon[1]-lon[0]))

    return Area


# In[4]:


#Change this to compute areas for one line of longitude and then use np.tile to complete the array
latitudes = np.linspace(-90, 90, 721)          
longitudes = np.linspace(-180, 179.75, 1440)

areas = []

for lat in latitudes[1:720]:

    row = []

    n = lat + .125
    s = lat - .125

    for lon in longitudes:
        e = lon + .125
        w = lon - .125

        row.append(calculate_area([s,n],[w,e]))

    areas.append(row)

row = []

for lon in longitudes:
    e = lon + .125
    w = lon - .125
    n = 90
    s = 89.875

    row.append(calculate_area([s,n],[w,e]))

areas.append(row)
areas.insert(0,row)

AREA_ARRAY = xr.DataArray(areas,dims=['latitude','longitude'])


# In[5]:


#Function takes a data array and returns the spatial average
def regional_mean(da, ocean_only=False):

    #Defining lat and lon variables
    lat = da.latitude
    lon = da.longitude

    #Longitude either goes from 0 to 360 or -180 to 180. We want to always have it be from -180 to 180.
    #If it is from 0 to 360 we transform the coordinates
    if lon.max() > 181:
        lonnew = (lon+180)%360 - 180
    else:
        lonnew=lon

    longrid, latgrid = np.meshgrid(lonnew, lat) #Turns lat and lon into matrices/grids

    #We then weight the data to account for spherical coordinates
    if ocean_only == True:
        oceanmask = xr.DataArray(globe.is_ocean(latgrid, longrid), dims=["latitude", "longitude"]) 
        oceanmask = oceanmask.where(oceanmask == True)
        gw_base = np.transpose(np.cos(np.asarray(lat) * np.pi / 180))
        gw = np.transpose(np.tile(gw_base, (len(lon), 1))) * oceanmask

    elif ocean_only == 'Land':
        oceanmask = xr.DataArray(globe.is_land(latgrid, longrid), dims=["latitude", "longitude"])
        oceanmask = oceanmask.where(oceanmask == True)
        gw_base = np.transpose(np.cos(np.asarray(lat) * np.pi / 180))
        gw = np.transpose(np.tile(gw_base, (len(lon), 1))) * oceanmask

    else:
        gw_base = np.transpose(np.cos(np.asarray(lat) * np.pi / 180))
        gw = np.transpose(np.tile(gw_base, (len(lon), 1)))

    gw = xr.DataArray(gw / np.nansum(gw), dims=["latitude", "longitude"])
    da_gw = da * gw
    out = da_gw.sum("latitude").sum("longitude")

    return out


# In[6]:

#This class is used to select and load in precipitation data and average the evaporation data
class data_subset:

    def __init__(self,latRange,lonRange, month):

        self.latRange = latRange
        self.lonRange = lonRange
        self.month = month

        self.coordinates = []
        self.precip = None
        self.evap = None

        self.regional_area = calculate_area(latRange, lonRange)

    def create_coordinates(self): #Creates a list of coordinate labels

        longitude = list(range(int(self.lonRange[0]),int(self.lonRange[1]),4))
        latitude = list(range(int(self.latRange[0]),int(self.latRange[1]),4))

        for s in latitude:

            for w in longitude: 

                if w < 0:
                    coord_name = f'output_n{str(abs(w)).zfill(3)}_'
                else:
                    coord_name = f'output_{str(w).zfill(4)}_'
                if s < 0:
                    coord_name = f'{coord_name}n{str(abs(s)).zfill(3)}'
                else:
                    coord_name = f'{coord_name}{str(s).zfill(4)}'

                self.coordinates.append(coord_name)

    def select_precip(self): #Load precipitation data

        if self.coordinates == []:
            self.create_coordinates()

        directory = "/glade/derecho/scratch/considine/11_16_f_30d"

        folders = [f"{directory}/{name}" for name in self.coordinates]

        if self.month == 0:
            target_substring = '*nc'
        else:
            target_substring = f'*-{str(self.month).zfill(2)}-*'

        datasets = []

        for folder in folders:

            dataset = glob.glob(f"{folder}/{target_substring}") 

            ds = xr.open_mfdataset(dataset, 
                   combine="nested", 
                   concat_dim="time", 
                   coords="minimal", 
                   data_vars="minimal", 
                   compat="override",
                   join="exact",
                   engine="netcdf4", 
                   decode_times=False 
                  )

            ds = ds.chunk({"time": 10, "latitude": -1, "longitude": -1}) 

            datasets.append(ds)

        combined_dataset = sum(datasets)

        self.precip = combined_dataset['p_track_lower'] + combined_dataset['p_track_upper']

    def spatial_avg_evap(self): #Takes spatial and temporal average of evaporation 

        global EVAP_DATA

        self.evap = EVAP_DATA.sel(latitude = slice(self.latRange[1], self.latRange[0]), 
                                  longitude = slice(self.lonRange[0], self.lonRange[1]))

        if self.month != 0:
            self.evap = self.evap.where(EVAP_DATA.valid_time.dt.month == self.month)

        self.evap = regional_mean(self.evap)

    def run_all(self): #Runs class methods in sequence

        self.create_coordinates()
        self.select_precip()
        self.spatial_avg_evap()



# In[1]:


#This function normalizes precipitation by evaporation then saves it to a netcdf file
def normalize_precip(latRange, lonRange, month, dir):

    data = data_subset(latRange, lonRange, month)
    data.run_all()

    evap_mean = data.evap.mean(dim='valid_time')
    evap_mean = evap_mean * data.regional_area

    precip_mean = data.precip.mean(dim='time')
    global AREA_ARRAY
    precip_mean = precip_mean * AREA_ARRAY

    normal_precip = precip_mean / evap_mean

    #Adding lat/lon_sw_corner so we have a coordinate for each sub region of data normalized
    normal_precip_w_coords = normal_precip.expand_dims(dim={"lat_sw_corner": [latRange[0]], "lon_sw_corner":[lonRange[0]]})

    normal_precip_w_coords.to_netcdf(dir)



# In[3]:

#Passes arguments into normalization function
arg1 = json.loads(sys.argv[1])
arg2 = json.loads(sys.argv[2])

normal_precip = normalize_precip(arg1, arg2, int(sys.argv[3]), sys.argv[4])

# In[ ]:




