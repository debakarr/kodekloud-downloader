from enum import Enum


class Quality(str, Enum):
    NHD = "360p"
    SD = "480p"
    QHD = "540p"
    HD = "720p"
    FHD = "1080p"
