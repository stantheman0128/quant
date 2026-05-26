import io, sys, glob, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import nvidia.cublas.lib
import nvidia.cudnn.lib
cublas_dir = pathlib.Path(nvidia.cublas.lib.__file__).parent
cudnn_dir = pathlib.Path(nvidia.cudnn.lib.__file__).parent
print("cublas dir:", cublas_dir)
print("cudnn dir:", cudnn_dir)
print("cublas dlls:", [p.split("\\")[-1] for p in glob.glob(str(cublas_dir / "*.dll"))])
print("cudnn dlls:", [p.split("\\")[-1] for p in glob.glob(str(cudnn_dir / "*.dll"))])
