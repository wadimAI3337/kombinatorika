"""k-means отдельно по светлым и тёмным полям -> контактные листы центроидов
   (как dvor/04_cluster.py)."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
exec(open("../dvor/04_cluster.py").read())
