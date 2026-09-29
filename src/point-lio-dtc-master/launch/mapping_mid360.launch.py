from launch import LaunchDescription
from launch.actions import GroupAction, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Declare the RViz argument
    rviz_arg = DeclareLaunchArgument(
        'rviz', default_value='true',#是否启动rviz2
        description='Flag to launch RViz.')

    # Node parameters, including those from the YAML configuration file
    laser_mapping_params = [
        PathJoinSubstitution([
            FindPackageShare('point_lio'),
            'config', 'mid360.yaml'#声明，最终以launch文件为准
        ]),
        {
            'use_imu_as_input': True,  # 让滤波/状态传播更偏向“IMU 输入模型”这条链路
            'prop_at_freq_of_imu': True, #状态传播（propagate）按 IMU 频率跑，而不是只在 LiDAR 帧到来时更新。
            'check_satu': True, #启用imu饱和检测，相当于一个imu保护，饱和阈值对应YAML里的 satu_acc / satu_gyro
            'init_map_size': 10, #初始化阶段/局部地图的初始规模（通常是“局部地图立方体/栅格”的初值）
            'point_filter_num': 1,  # Options: 1, 3。设 1：保留点多，细节多，但算力压力大、噪声也多。设 3：更稀更快，但纹理少的场景可能更容易匹配不稳。
            'space_down_sample': True, #开启空间降采样（一般就是体素/网格下采样）。
            'filter_size_surf': 0.7,  # Options: 0.5, 0.3, 0.2, 0.15, 0.1。当前帧（scan/平面特征）降采样体素大小（越大越稀、越快）。
            'filter_size_map': 0.7,  # Options: 0.5, 0.3, 0.15, 0.1 地图（ikdtree/局部地图）维护用的降采样体素大小。
            'cube_side_length': 1000.0,  # Option: 1000 局部地图分块（立方体）边长
            'runtime_pos_log_enable': False,  # Option: True 排查漂移/复现实验时再开，平时关掉省 IO。
        }
    ]

    # Node definition for laserMapping with Point-LIO
    laser_mapping_node = Node(
        package='point_lio',
        executable='pointlio_mapping',
        name='laserMapping',
        output='screen',
        parameters=laser_mapping_params,
        # prefix='gdb -ex run --args'
    )
    # Node definition for laserMapping with Point-LIO
    post_mapping_node = Node(
        package='point_lio',
        executable='post_mapper',
        name='post_mapping',
        output='screen',
        parameters=laser_mapping_params,
        # prefix='gdb -ex run --args'
    )

    # Conditional RViz node launch
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz',
        arguments=['-d', PathJoinSubstitution([
            FindPackageShare('point_lio'),
            'rviz_cfg', 'loam_livox.rviz'
        ])],
        condition=IfCondition(LaunchConfiguration('rviz')),
        prefix='nice'
    )

    # Assemble the launch description
    ld = LaunchDescription([
        rviz_arg,
        laser_mapping_node,
        # post_mapping_node,
        GroupAction(
            actions=[rviz_node],
            condition=IfCondition(LaunchConfiguration('rviz'))
        ),
    ])

    return ld
