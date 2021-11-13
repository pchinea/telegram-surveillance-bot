################
Surveillance Bot
################

.. image:: https://github.com/pchinea/telegram-surveillance-bot/actions/workflows/tests.yml/badge.svg?branch=master
    :target: https://github.com/pchinea/telegram-surveillance-bot/actions/workflows/tests.yml
    :alt: Build status

.. image:: https://codecov.io/gh/pchinea/telegram-surveillance-bot/branch/master/graph/badge.svg?token=z96qOgGyMq
    :target: https://codecov.io/gh/pchinea/telegram-surveillance-bot
    :alt: Coverage

.. image:: https://img.shields.io/pypi/pyversions/surveillance-bot
    :target: https://pypi.org/project/surveillance-bot
    :alt: PyPI - Python Version

.. image:: https://img.shields.io/badge/License-GPLv3-blue.svg
    :target: https://github.com/pchinea/telegram-surveillance-bot/blob/master/LICENSE.txt
    :alt:  License

Surveillance Bot is a Telegram bot that uses a camera (such a webcam) for
surveillance. Photos and videos can be taken from the camera and sent via
Telegram instantly. Those actions can be triggered by commands sent by the
user or when motion is detected.

All files in this project are covered under the `GPLv3 LICENSE
<http://www.gnu.org/licenses/gpl.html>`_, if you modify this project in any
way you MUST publish the changes you made and submit your contribution to the
community under the same license.

Features
********

- Motion detection.
- Real time notification.
- Motion tracking.
- Photo and video capture on demand.
- Bot configuration via telegram chat.
- Timestamp in photos and videos.
- H264 video encoding (when codec is available).
- Multi-platform: Linux, Windows and MacOS.
- Dockerized.

Requirements
************
- python (supported versions: 3.6, 3.7, 3.8 and 3.9)
- OpenCV
- python-telegram-bot

Quick-start
***********

1. Install package with ``pip``::

    pip install surveillance-bot

2. Set application configuration variables (see `Advanced configuration`_)::

    export BOT_API_TOKEN=<api_token>
    export AUTHORIZED_USER=<username>

3. Run script::

    surveillance_bot

Advanced configuration
**********************
The application is configured using this environment variables:
  - ``BOT_API_TOKEN`` *(mandatory)*

    The `Telegram bot API <https://core.telegram.org/bots/api>`_ token of a
    telegram bot.

  - ``AUTHORIZED_USER`` *(mandatory)*

    The `Telegram username
    <https://telegram.org/faq#q-what-are-usernames-how-do-i-get-one>`_
    (without @) of the user authorized to interact with the bot.

  - ``PERSISTENCE_DIR``

    If this variable is set the bot configuration (set via telegram chat) will
    persist on disk into a file placed in this directory.

  - ``LOG_LEVEL``

    Global log level for application and libraries using the
    `python standard logging library
    <https://docs.python.org/3/library/logging.html#logging-levels>`_.

  - ``BOT_LOG_LEVEL``

    Specific Bot application log level.

H264 Encoding
*************

This application generates MP4 video files, if H264 codec is available it will
use it to generate smaller files.

The OpenCV library provided by the PyPi package (installed with pip)
`doesn't have H264 support
<https://github.com/skvark/opencv-python/issues/81#issuecomment-376166468>`_
so if you wish to use H264 encoding you have to do a manual build or use a
precompiled library with H264 support (some distributions, like Ubuntu, have
OpenCV library supporting this codec).

Docker
******

Dockerfile
==========

A **Surveillance Bot** docker image can be created, using the Dockerfile
provided, running this command::

    docker build -t telegram-surveillance-bot .

This docker image has H264 support. The image will be created with UTC timezone
by default (so photo and video timestamp will use this timezone) it can be
overridden mounting ``/etc/localtime`` file (see `docker-compose.yml
<https://github.com/pchinea/telegram-surveillance-bot/blob/master/docker-compose.yml>`_
example).

docker-compose
==============

A docker-compose example file is also provided, you must previously export the
required configuration variables or modify this docker-compose template.

Screenshots
***********

Start command
=============

.. image:: https://github.com/pchinea/telegram-surveillance-bot/raw/master/img/start.png
   :alt: Start command

Config command
==============

.. image:: https://github.com/pchinea/telegram-surveillance-bot/raw/master/img/config.jpg
   :alt: Config command

Surveillance sequence screencast
================================

.. image:: https://github.com/pchinea/telegram-surveillance-bot/raw/master/img/surveillance.gif
   :alt: Surveillance sequence

Video taken in surveillance mode
================================

.. image:: https://github.com/pchinea/telegram-surveillance-bot/raw/master/img/motion.gif
   :alt: Motion video


