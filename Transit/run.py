import os

os.system("gnome-terminal -e 'bash -c \"python AggregationService.py; exec bash\"'")
os.system("gnome-terminal -e 'bash -c \"python CrimeService.py; exec bash\"'")
os.system("gnome-terminal -e 'bash -c \"python ManagementService.py; exec bash\"'")
os.system("gnome-terminal -e 'bash -c \"python POIService.py; exec bash\"'")
os.system("gnome-terminal -e 'bash -c \"python UnionService.py; exec bash\"'")
os.system("gnome-terminal -e 'bash -c \"python TransitService.py; exec bash\"'")
