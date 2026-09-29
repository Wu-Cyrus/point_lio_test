# 雷达调参说明

在文件根目录（`/dev/src`）下，共有两个文件夹是关于雷达定位的：

- `livox_ros_driver2`：雷达的 ROS 驱动。
- `point-lio-dtc-master`：雷达里程计核心代码。

> 本文由原 Word 文档转换而来，配置截图已整理为代码片段。原文中的启动命令含省略号，使用时需要补全实际文件名；代码片段中的 IP 和路径沿用原截图。

## livox_ros_driver2（雷达的 ROS 驱动）

### 准备

先根据 README，对 Livox SDK2 进行 build。

### 配置雷达

在 `config` 里的 `mid360_config.json` 中，需要配置雷达 IP 地址和电脑 IP 地址，也就是网线连接后的有线网络 IP。

`host_net_info` 里面的所有 IP 都要改成电脑的 IP，这个可以自己设置。下面 `lidar_configs` 的 IP 只需要改后两位，也是雷达上面贴的二维码下面的最后两个字母，这个也能通过连接网线进行设置。（我不知道学长你那个有没有标签，可能需要先用上位机设置一下？）

> 文件名大小写提示：原文写作 `mid360_config.json`，下方 launch 截图中使用的是 `MID360_config.json`，请以实际文件名为准。

原截图中的配置片段如下。为方便阅读，分为两个片段展示；它们不是完整配置文件。

```json
"host_net_info": {
  "cmd_data_ip": "192.168.1.100",
  "cmd_data_port": 56101,
  "push_msg_ip": "192.168.1.100",
  "push_msg_port": 56201,
  "point_data_ip": "192.168.1.100",
  "point_data_port": 56301,
  "imu_data_ip": "192.168.1.100",
  "imu_data_port": 56401,
  "log_data_ip": "",
  "log_data_port": 56501
}
```

```json
"lidar_configs": [
  {
    "ip": "192.168.1.196",
    "pcl_data_type": 1,
    "pattern_mode": 0,
    "extrinsic_parameter": {
      "roll": 0.0,
      "pitch": 0.0,
      "yaw": 0.0,
      "x": 0,
      "y": 0,
      "z": 0
    }
  }
]
```

### 关于调参

配置文件：`livox_ros_driver2/launch_ROS2/msg_MID360_launch.py`。

调整 `publish_freq` 可以改变发布帧率。太高可能会抖动，一般取 30–50。

原截图中的参数配置：

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import launch

# User configure parameters for ROS 2
xfer_format = 1    # 0-Pointcloud2(PointXYZRTL), 1-customized pointcloud format
multi_topic = 0    # 0-All LiDARs share the same topic, 1-One LiDAR one topic
data_src = 0       # 0-lidar, others-Invalid data src
publish_freq = 50.0  # Frequency of publish: 5.0, 10.0, 20.0, 50.0, etc.
output_type = 0
frame_id = 'livox_frame'
lvx_file_path = '/home/livox/livox_test.lvx'
cmdline_bd_code = 'livox0000000001'

cur_path = os.path.split(os.path.realpath(__file__))[0] + '/'
cur_config_path = cur_path + '../config'
user_config_path = os.path.join(cur_config_path, 'MID360_config.json')

livox_ros2_params = [
    {"xfer_format": xfer_format},
    {"multi_topic": multi_topic},
    {"data_src": data_src},
    {"publish_freq": publish_freq},
    {"output_data_type": output_type},
    {"frame_id": frame_id},
    {"lvx_file_path": lvx_file_path},
    {"user_config_path": user_config_path},
    {"cmdline_input_bd_code": cmdline_bd_code}
]
```

截图中的节点创建片段：

```python
def generate_launch_description():
    livox_driver = Node(
        package='livox_ros_driver2',
        executable='livox_ros_driver2_node',
        name='livox_lidar_publisher',
        output='screen',
        parameters=livox_ros2_params
    )
```

截图下方还包含 `return LaunchDescription([`、`livox_driver,`，以及未完整显示的事件处理注释；以上只转录完整可读的节点创建部分，不作为完整 launch 文件。

### 使用 launch

原文命令（文件名未写全）：

```bash
ros2 launch livox_ros_driver2 msg_mid360...
```

## point-lio-dtc-master（雷达里程计核心代码）

### 准备

按照 README 下载 `fmt`。

可能还需要安装 `abseil` 等一系列库，按照 build 的报错安装即可。我也不太确定学长你的电脑可能缺啥 >^<。

### 关于调参

整体使用思路是先建图，然后根据建好的图使用。

一开始启动雷达的时候要保持静止，建图的起点也是每次启动需要的起点。（GPS 我还没搞，这个假期搞一下。）但是有容错，不需要特别准，比如角度偏个 30 度、位置差点都没啥问题，都会归到起点。

#### mid360.yaml

配置文件：`point-lio-dtc-master/config/mid360.yaml`。

1. **纯里程计／建图模式**：在 `config/mid360.yaml` 中设置 `use_prior_map` 为 `false`。如需要保存地图，则设置 `pcd_save_en` 为 `true`，可以自行调整保存帧数或进行后处理。
2. **先验地图定位**：在 `config/mid360.yaml` 中设置 `use_prior_map` 为 `true`，设置地图路径 `prior_map_path`，设置 yaw 搜索范围 `yaw_range`（格式：起始值、间隔、终止值）。
3. **里程计发布帧率**：里程计的发布帧率与雷达点云发布帧率相同，调整雷达驱动的帧率设置即可改变里程计帧率。也可以修改代码，发布 IMU 的 KF 状态估计；IMU 更新频率为 200 Hz，理论上可以以该频率发布。

> 原文中的 `ture` 已按布尔值拼写修正为 `true`。

#### mapping_mid360.launch.py

配置文件：`point-lio-dtc-master/launch/mapping_mid360.launch.py`。

通过调整下面的参数改变降采样：越小越精确但慢，越大越稀疏但快。

```python
'filter_size_surf': 0.7,  # Options: 0.5, 0.3, 0.2, 0.15, 0.1
'filter_size_map': 0.7,   # Options: 0.5, 0.3, 0.15, 0.1
```

- `filter_size_surf`：当前帧（scan／平面特征）降采样体素大小，越大越稀、越快。
- `filter_size_map`：地图（ikdtree／局部地图）维护用的降采样体素大小。

截图中同时显示了以下相邻配置：

```python
'check_satu': True,
'init_map_size': 10,
'point_filter_num': 1,
'space_down_sample': True,
'cube_side_length': 1000.0,
'runtime_pos_log_enable': False,
```

- `check_satu`：启用 IMU 饱和检测；截图注释说明饱和阈值对应 YAML 里的 `satu_acc`、`satu_gyro`。
- `init_map_size`：初始化阶段／局部地图的初始规模，通常是“局部地图立方体／栅格”的初值。
- `point_filter_num`：可选 1、3。设为 1 时保留点多、细节多，但算力压力大、噪声也多；设为 3 时更稀更快，但纹理少的场景可能更容易匹配不稳。
- `space_down_sample`：开启空间降采样，一般就是体素／网格下采样。
- `cube_side_length`：局部地图分块（立方体）边长，截图给出的值为 1000。
- `runtime_pos_log_enable`：排查漂移／复现实验时再开，平时关闭以节省 IO。

### 使用 launch

原文命令（文件名未写全）：

```bash
ros2 launch point_lio mapping_mid360...
```

## 其他

1. **参数配置**：`config`、`launch` 文件中能够配置大部分参数，包括地图分辨率、IMU 协方差。有些参数目前没有写入配置文件中，如 ICP 迭代次数，见文件 `scan_aligner` 中的 `max_iter` 配置。
2. **`/PCD`**：保存先验地图点云文件的默认文件夹。每次保存的名字是一样的，不及时备份会被覆盖。
3. **`/rviz_cfg`**：RViz 配置文件，默认了打开 RViz2 可视化的内容，可以自行调整。在 RViz2 中调整设置后，覆盖该配置文件即可。

## 附加

最后，我在 `src` 里还写了一个对 TF 数据处理的节点，其中把 m 单位改为 mm 单位，yaw 角进行了映射。

这个节点可用可不用，主要就是方便下游订阅，其实也可以直接订阅 `/tf`。目前的结果是得到雷达自身的 `xyz + yaw`，但是还可以根据需求添加加速度，以及加入关于车身的坐标转换，得到车中心的坐标。
