# CPU and Memory Stress Test Tool

A Python-based utility for stress testing CPU and memory usage in a configurable, cyclical pattern. Useful for testing auto-scaling, performance monitoring, and resource utilization in containerized environments.

## Features

- **Gradual Resource Ramping**: CPU and memory usage increases and decreases in configurable steps
- **Cyclical Patterns**: Alternates between high and low resource utilization phases
- **Configurable Parameters**: All key parameters can be adjusted via environment variables
- **Container-Ready**: Includes Dockerfile for easy deployment in containerized environments
- **Resource Baseline**: Maintains a configurable percentage of resources during low phases

## Quick Start

### Running with Docker

1. Build the Docker image:
   ```
   docker build -t stress-test-app .
   ```

2. Run with default settings:
   ```
   docker run --rm -it stress-test-app
   ```

3. Run with custom configuration:
   ```
   docker run --rm -it \
     -e HIGH_STRESS_DURATION=120 \
     -e LOW_STRESS_DURATION=300 \
     -e MAX_CPU_CORES=1 \
     -e MAX_MEMORY_MB=1024 \
     -e RAMP_STEPS=10 \
     -e LOW_PHASE_PERCENT=0.2 \
     -e STARTUP_RANDOM_DELAY_MAX_SEC=10 \
     stress-test-app
   ```

### Running Directly

If you have Python installed, you can run the script directly:

```
python stressor.py
```

## Kubernetes Deployment

You can deploy this application to a Kubernetes cluster using a Deployment manifest. Below is an example `deployment.yaml` that sets all configurable environment variables:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stress-test-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: stress-test-app
  template:
    metadata:
      labels:
        app: stress-test-app
    spec:
      containers:
      - name: stress-test-app
        image: ghcr.io/sabbour/stressor:latest
        env:
        - name: HIGH_STRESS_DURATION
          value: "120"
        - name: LOW_STRESS_DURATION
          value: "300"
        - name: RAMP_STEPS
          value: "10"
        - name: RAMP_UP_DURATION
          value: "20"
        - name: RAMP_DOWN_DURATION
          value: "20"
        - name: LOW_PHASE_PERCENT
          value: "0.1"
        - name: MAX_CPU_CORES
          value: "2"
        - name: MAX_MEMORY_MB
          value: "1024"
        - name: STARTUP_RANDOM_DELAY_MAX_SEC
          value: "10"
        resources:
          limits:
            cpu: "2"
            memory: "1024Mi"
          requests:
            cpu: "1"
            memory: "512Mi"
```

Apply the deployment with:

```
kubectl apply -f deployment.yaml
```

You can adjust the environment variable values and resource requests/limits as needed for your environment.

## Multiple Replica Deployments

This application is designed to work well in multi-replica environments such as Kubernetes. When running multiple replicas:

- Each replica operates independently with its own resource cycle
- No coordination is required between replicas
- Each replica applies a random startup delay to prevent synchronized resource usage patterns

## Configuration

The following environment variables can be used to configure the stress test:

| Environment Variable        | Description                                     | Default Value     |
|-----------------------------|-------------------------------------------------|-------------------|
| HIGH_STRESS_DURATION       | Duration of high stress phase in seconds        | 120 (2 mins)      |
| LOW_STRESS_DURATION        | Duration of low stress phase in seconds         | 300 (5 mins)      |
| RAMP_STEPS                 | Number of steps for ramp-up and ramp-down       | 10                |
| RAMP_UP_DURATION           | Duration of the ramp-up phase in seconds        | 20                |
| RAMP_DOWN_DURATION         | Duration of the ramp-down phase in seconds      | 20                |
| LOW_PHASE_PERCENT          | Resource % to maintain during low phase (0-1)   | 0.1 (10%)         |
| MAX_CPU_CORES              | Maximum number of CPU cores to stress           | All available     |
| MAX_MEMORY_MB              | Maximum memory to allocate in MB                | 1024              |
| STARTUP_RANDOM_DELAY_MAX_SEC | Maximum random delay at startup in seconds    | 30                |

## How It Works

The script follows this cycle:

1. **Ramp Up**: Gradually increases CPU and memory usage in steps over 20 seconds
2. **Hold Peak**: Maintains peak resource utilization for 5 minutes (300 seconds)
3. **Ramp Down**: Gradually decreases CPU and memory usage in steps over 20 seconds
4. **Low Phase**: Maintains the configured baseline percentage of resources for 5 minutes
5. Repeat from step 1

## Use Cases

- Testing Kubernetes Horizontal Pod Autoscaler (HPA)
- Testing Kubernetes Vertical Pod Autoscaler (VPA)
- Validating monitoring and alerting systems
- Performance testing of applications under varying resource constraints
- Testing cloud provider auto-scaling capabilities

## Notes

- The script handles graceful shutdown with SIGINT (Ctrl+C)
- During testing, monitor your system to ensure you're not causing resource starvation
- In containerized environments, the script will be limited by the container's resource limits
