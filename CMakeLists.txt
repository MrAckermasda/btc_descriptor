cmake_minimum_required(VERSION 3.0.2)
project(btc_desc)


## Compile as C++11, supported in ROS Kinetic and newer

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 17)
SET(CMAKE_BUILD_TYPE "Release")
#SET(CMAKE_CXX_FLAGS_DEBUG "$ENV{CXXFLAGS} -O0 -Wall -g -ggdb")
#SET(CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} -O3 -Wall")
## Find catkin macros and libraries
## if COMPONENTS list like find_package(catkin REQUIRED COMPONENTS xyz)
## is used, also find other catkin packages
find_package(catkin REQUIRED COMPONENTS
  cv_bridge
  pcl_conversions
  pcl_ros
  roscpp
  rospy
  sensor_msgs
  std_msgs
  tf_conversions
)

## System dependencies are found with CMake's conventions
find_package(Boost REQUIRED COMPONENTS system)
find_package(PCL REQUIRED)
find_package(OpenCV REQUIRED)
find_package(Threads)
find_package(Ceres REQUIRED)
find_package(GTSAM REQUIRED QUIET)
find_package(CUDA REQUIRED)

if(NOT TARGET CUDA::cublas)
    add_library(CUDA::cublas INTERFACE IMPORTED)
    set_target_properties(CUDA::cublas PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${CUDA_INCLUDE_DIRS}"
        INTERFACE_LINK_LIBRARIES "${CUDA_cublas_LIBRARY}"
    )
endif()

if(NOT TARGET CUDA::cusparse)
    add_library(CUDA::cusparse INTERFACE IMPORTED)
    set_target_properties(CUDA::cusparse PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${CUDA_INCLUDE_DIRS}"
        INTERFACE_LINK_LIBRARIES "${CUDA_cusparse_LIBRARY}"
    )
endif()

if(NOT TARGET CUDA::cusolver)
    add_library(CUDA::cusolver INTERFACE IMPORTED)
    set_target_properties(CUDA::cusolver PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${CUDA_INCLUDE_DIRS}"
        INTERFACE_LINK_LIBRARIES "${CUDA_cusolver_LIBRARY}"
    )
endif()

if(NOT TARGET CUDA::cudart)
    add_library(CUDA::cudart INTERFACE IMPORTED)
    set_target_properties(CUDA::cudart PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${CUDA_INCLUDE_DIRS}"
        INTERFACE_LINK_LIBRARIES "${CUDA_cudart_LIBRARY}"
    )
endif()

if(CUDA_FOUND)
    message("=== CUDA 信息 ===")
    message("CUDA_VERSION: ${CUDA_VERSION}")
    message("cusolver: ${CUDA_cusolver_LIBRARY}")
    message("cudart: ${CUDA_cudart_LIBRARY}")
    message("cusparce: ${CUDA_cusparce_LIBRARY}")
    message("cublas: ${CUDA_cusolver_LIBRARY}")
    message("CUDA_LIBRARIES: ${CUDA_LIBRARIES}")

else()
    message("CUDA not found")
endif()


set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

catkin_package(
 CATKIN_DEPENDS roscpp rospy std_msgs
)

include_directories(
# include
  ${catkin_INCLUDE_DIRS}
  ${PCL_INCLUDE_DIRS}
  ${OpenCV_INCLUDE_DIRS}
  ${CUDA_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
  
)

add_library(utils_lib src/utils.cpp)
target_link_libraries(utils_lib ${PCL_LIBRARIES} ${catkin_LIBRARIES})

add_library(btc_lib src/btc.cpp)
target_include_directories(btc_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(btc_lib ${PCL_LIBRARIES} ${catkin_LIBRARIES} ${OpenCV_LIBS} ${CERES_LIBRARIES} tbb ${CUDA_LIBRARIES} ${CUDA_cusolver_LIBRARY})


add_executable(btc_place_recognition example/place_recognition.cpp)
target_link_libraries(btc_place_recognition
    btc_lib
    utils_lib)

add_executable(btc_extractor example/btc_extractor.cpp)
target_link_libraries(btc_extractor
    btc_lib
    utils_lib)

add_executable(btc_recognizer example/btc_recognizer.cpp)
target_link_libraries(btc_recognizer
    btc_lib
    utils_lib)








