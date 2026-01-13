import os
from phoenix.otel import register
from opentelemetry import trace
from dotenv import load_dotenv

load_dotenv()

def init_observability():
    """
    Initializes Arize Phoenix observability via OpenTelemetry.
    Traces are sent to the local Phoenix collector.
    """
    phoenix_url = os.getenv("PHOENIX_COLLECTOR_URL", "http://localhost:6006/v1/traces")
    
    # Register Arize Phoenix as the trace exporter
    tracer_provider = register(
        project_name="local-agent-mlops",
        endpoint=phoenix_url,
    )
    
    # Optional: Also log to console for debugging
    # tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    
    print(f"Observability initialized. Traces sent to: {phoenix_url}")
    return tracer_provider

def get_tracer(name: str):
    return trace.get_tracer(name)

if __name__ == "__main__":
    provider = init_observability()
    tracer = get_tracer("test-tracer")
    with tracer.start_as_current_span("test-span"):
        print("Traced span created.")
