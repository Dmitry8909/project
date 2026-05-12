from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://blog:blog_pass@localhost:5432/blog"
    rabbitmq_url: str = "amqp://blog:blog_pass@localhost:5672/"
    redis_url: str = "redis://localhost:6379/0"
    redis_timeline_url: str = "redis://localhost:6380/0"
    redis_timeline_cluster: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    scylla_contact_points: str = "localhost"
    scylla_keyspace: str = "blog"
    jwt_secret: str = "super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "blog-media"
    minio_secure: bool = False

    celebrity_follower_threshold: int = 10000
    hot_cache_ttl: int = 300
    timeline_ttl: int = 604800

    citus_worker_nodes: str = "citus-worker-1,citus-worker-2"

    service_name: str = "shared"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
