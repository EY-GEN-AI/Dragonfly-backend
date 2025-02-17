from diskcache import Cache
 
 
cache_dir = "./cache_directory"
cache = Cache(cache_dir)
 
cache.delete('Which sales orders have experienced OTIF (On-Time, In-Full) failures and are impacted the most?')