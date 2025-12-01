

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler
import json
import random

class AirportFiltering:
    """
    This AirportFiltering class provides functionality to filter and select airports and their runways based on various filters:

      - **Filter airports** by country, continent, region, airport type, ICAO code prefix, elevation...
      - **Filter runways** by length, width, and type.
      - **Select random airports** from the filtered results.
      - **Retrieve runways** associated with the selected airports.
    """
    def __init__(self, airports_file, runways_file, runways_database_file):
        # We need to keep 'na' as North America is set as 'NA'
        self.airports_df = pd.read_csv(airports_file, sep=';', keep_default_na=False)
        self.runways_df = pd.read_csv(runways_file, sep=';')
        with open(runways_database_file, 'r') as f:
            self.runways_database = json.load(f)
        
        # Merge airports and runways data
        self.merged_df = pd.merge(self.airports_df, self.runways_df, left_on='ident', right_on='@ident', how='inner')
        # Initialize filtered df
        self.filtered_df = self.merged_df.copy()
        
    def filter_by_country(self, countries):
        if isinstance(countries, str):
            countries = [countries]
        self.filtered_df = self.filtered_df[self.filtered_df['iso_country'].isin(countries)]
        return self
    
    def filter_by_airport_type(self, types):
        if isinstance(types, str):
            types = [types]
        self.filtered_df = self.filtered_df[self.filtered_df['type'].isin(types)]
        return self
    
    def filter_by_region(self, regions):
        if isinstance(regions, str):
            regions = [regions]
        self.filtered_df = self.filtered_df[self.filtered_df['iso_region'].isin(regions)]
        return self
    
    def filter_by_continent(self, continents):
        if isinstance(continents, str):
            continents = [continents]
        self.filtered_df = self.filtered_df[self.filtered_df['continent'].isin(continents)]
        return self
    
    def filter_by_icao_prefix(self, prefixes):
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        self.filtered_df = self.filtered_df[self.filtered_df['ident'].str.startswith(tuple(prefixes))]
        return self
    
    def filter_by_elevation(self, min_elevation=None, max_elevation=None):
        if min_elevation is not None:
            self.filtered_df = self.filtered_df[self.filtered_df['elevation_ft'] >= min_elevation]
        if max_elevation is not None:
            self.filtered_df = self.filtered_df[self.filtered_df['elevation_ft'] <= max_elevation]
        return self
    
    def filter_by_runway_length(self, min_length=None, max_length=None):
        if min_length is not None:
            self.filtered_df = self.filtered_df[self.filtered_df['@length'] >= min_length]
        if max_length is not None:
            self.filtered_df = self.filtered_df[self.filtered_df['@length'] <= max_length]
        return self
    
    def filter_by_runway_width(self, min_width=None, max_width=None):
        if min_width is not None:
            self.filtered_df = self.filtered_df[self.filtered_df['@width'] >= min_width]
        if max_width is not None:
            self.filtered_df = self.filtered_df[self.filtered_df['@width'] <= max_width]
        return self
    
    # Selection random airports from currently filtered list
    def select_random_airports(self, num_airports):
        airports = self.filtered_df['ident'].unique()
        selected_airports = random.sample(list(airports), min(num_airports, len(airports)))
        return selected_airports


    def filter_by_number_of_runways(self, single_runway=True):
        runway_counts = self.runways_df.groupby('@ident').size().reset_index(name='runway_count')
        airports_df = self.filtered_df[['ident']].drop_duplicates()
        airports_df = airports_df.merge(runway_counts, left_on='ident', right_on='@ident', how='left')
        airports_df['runway_count'] = airports_df['runway_count'].fillna(0).astype(int)
        
        if single_runway:
            airports_to_keep = airports_df[airports_df['runway_count'] == 1]['ident']
        else:
            airports_to_keep = airports_df[airports_df['runway_count'] > 1]['ident']
        
        self.filtered_df = self.filtered_df[self.filtered_df['ident'].isin(airports_to_keep)]        
        return self

    
    def get_filtered_df_length(self):
        return len(self.filtered_df)
    
    # Extract airport_runways lists from selected airports
    def get_airports_runways(self, selected_airports):
        airports_runways = {}
        for airport in selected_airports:
            if airport in self.runways_database:
                # Get all runways for this airport
                runways = list(self.runways_database[airport].keys())
                airports_runways[airport] = runways
        return airports_runways
    
    def reset_filters(self):
        self.filtered_df = self.merged_df.copy()
        return self
    
