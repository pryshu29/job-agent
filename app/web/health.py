import logging
import os

from flask import Flask, jsonify

from app.database import check_database_connection


logger = logging.getLogger(
    "AI_JOB_AGENT.WEB"
)


app = Flask(
    __name__
)


@app.route(
    "/",
    methods=["GET"],
)
def home():

    logger.info(
        "HEALTH | Root health check received"
    )

    return jsonify(
        {
            "status": "healthy",
            "service": "AI_JOB_AGENT",
        }
    )


@app.route(
    "/health",
    methods=["GET"],
)
def health():

    logger.info(
        "HEALTH | Health check received"
    )

    return jsonify(
        {
            "status": "healthy",
            "service": "AI_JOB_AGENT",
        }
    )


@app.route(
    "/ready",
    methods=["GET"],
)
def ready():

    logger.info(
        "HEALTH | Readiness check received"
    )

    try:

        check_database_connection()

        logger.info(
            "HEALTH | Readiness check successful"
        )

        return jsonify(
            {
                "status": "ready",
                "service": "AI_JOB_AGENT",
                "database": "healthy",
            }
        ), 200

    except Exception:

        logger.exception(
            "HEALTH | Readiness check failed"
        )

        return jsonify(
            {
                "status": "not_ready",
                "service": "AI_JOB_AGENT",
                "database": "unavailable",
            }
        ), 503


def run_web():

    port = int(
        os.environ.get(
            "PORT",
            10000,
        )
    )

    logger.info(
        "WEB | Starting health server | port=%s",
        port,
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )