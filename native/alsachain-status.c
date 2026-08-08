#include <alsa/asoundlib.h>
#include <alsa/pcm_external.h>
#include <alloca.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct alsachain_status { snd_pcm_ioplug_t io; snd_pcm_t *slave; char *path; };
static void write_state(struct alsachain_status *status, const char *state) {
  int fd = open(status->path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
  if (fd < 0) { SNDERR("Cannot write status %s: %s", status->path, strerror(errno)); return; }
  dprintf(fd, "pid: %ld\nstate: %s\nrate: %u\nformat: %s\nchannels: %u\n", (long)getpid(), state, status->io.rate, snd_pcm_format_name(status->io.format), status->io.channels);
  close(fd);
}
static int start(snd_pcm_ioplug_t *io) { struct alsachain_status *s = io->private_data; int e = snd_pcm_start(s->slave); if (e >= 0) write_state(s, "Playing"); return e; }
static int stop(snd_pcm_ioplug_t *io) { struct alsachain_status *s = io->private_data; int e = snd_pcm_drop(s->slave); if (e >= 0) write_state(s, "Prepared"); return e; }
static snd_pcm_sframes_t pointer(snd_pcm_ioplug_t *io) { struct alsachain_status *s = io->private_data; snd_pcm_sframes_t d = 0; if (snd_pcm_delay(s->slave, &d) < 0 || !io->buffer_size) return 0; return (io->appl_ptr - (d > 0 ? (snd_pcm_uframes_t)d : 0)) % io->buffer_size; }
static snd_pcm_sframes_t transfer(snd_pcm_ioplug_t *io, const snd_pcm_channel_area_t *a, snd_pcm_uframes_t off, snd_pcm_uframes_t size) { unsigned int bits = snd_pcm_format_physical_width(io->format) * io->channels; if (!bits || a[0].step != bits || a[0].first % 8) return -EINVAL; struct alsachain_status *s = io->private_data; return snd_pcm_writei(s->slave, (unsigned char *)a[0].addr + a[0].first / 8 + off * a[0].step / 8, size); }
static int hw_params(snd_pcm_ioplug_t *io, snd_pcm_hw_params_t *p) { struct alsachain_status *s = io->private_data; snd_pcm_hw_params_t *sp; snd_pcm_format_t f; unsigned int c, r; int d = 0, e; if ((e = snd_pcm_hw_params_get_format(p, &f)) < 0 || (e = snd_pcm_hw_params_get_channels(p, &c)) < 0 || (e = snd_pcm_hw_params_get_rate(p, &r, &d)) < 0) return e; snd_pcm_hw_params_alloca(&sp); if ((e = snd_pcm_hw_params_any(s->slave, sp)) < 0 || (e = snd_pcm_hw_params_set_access(s->slave, sp, SND_PCM_ACCESS_RW_INTERLEAVED)) < 0 || (e = snd_pcm_hw_params_set_format(s->slave, sp, f)) < 0 || (e = snd_pcm_hw_params_set_channels(s->slave, sp, c)) < 0 || (e = snd_pcm_hw_params_set_rate(s->slave, sp, r, 0)) < 0) return e; return snd_pcm_hw_params(s->slave, sp); }
static int prepare(snd_pcm_ioplug_t *io) { struct alsachain_status *s = io->private_data; int e = snd_pcm_prepare(s->slave); if (e >= 0) write_state(s, "Prepared"); return e; }
static int pause_pcm(snd_pcm_ioplug_t *io, int on) { struct alsachain_status *s = io->private_data; int e = snd_pcm_pause(s->slave, on); if (e >= 0) write_state(s, on ? "Paused" : "Playing"); return e; }
static int drain(snd_pcm_ioplug_t *io) { struct alsachain_status *s = io->private_data; int e = snd_pcm_drain(s->slave); if (e >= 0) write_state(s, "Prepared"); return e; }
static int close_pcm(snd_pcm_ioplug_t *io) { struct alsachain_status *s = io->private_data; snd_pcm_close(s->slave); free(s->path); free(s); return 0; }
static int poll_count(snd_pcm_ioplug_t *io) { return snd_pcm_poll_descriptors_count(((struct alsachain_status *)io->private_data)->slave); }
static int poll_desc(snd_pcm_ioplug_t *io, struct pollfd *p, unsigned int n) { return snd_pcm_poll_descriptors(((struct alsachain_status *)io->private_data)->slave, p, n); }
static int poll_events(snd_pcm_ioplug_t *io, struct pollfd *p, unsigned int n, unsigned short *r) { return snd_pcm_poll_descriptors_revents(((struct alsachain_status *)io->private_data)->slave, p, n, r); }
static const snd_pcm_ioplug_callback_t callbacks = { .start=start,.stop=stop,.pointer=pointer,.transfer=transfer,.close=close_pcm,.hw_params=hw_params,.prepare=prepare,.drain=drain,.pause=pause_pcm,.poll_descriptors_count=poll_count,.poll_descriptors=poll_desc,.poll_revents=poll_events };
SND_PCM_PLUGIN_DEFINE_FUNC(alsachain_status) { snd_config_iterator_t i,n; const char *path = NULL, *slave = NULL; struct alsachain_status *s; unsigned int access = SND_PCM_ACCESS_RW_INTERLEAVED; unsigned int formats[] = {SND_PCM_FORMAT_S16_LE,SND_PCM_FORMAT_S24_3LE,SND_PCM_FORMAT_S24_LE,SND_PCM_FORMAT_S32_LE,SND_PCM_FORMAT_FLOAT_LE}; int e = 0; if (stream != SND_PCM_STREAM_PLAYBACK) return -EINVAL; snd_config_for_each(i,n,conf) { snd_config_t *node=snd_config_iterator_entry(i); const char *id; if (snd_config_get_id(node,&id)<0) continue; if (!strcmp(id,"status_path")) e=snd_config_get_string(node,&path); else if (!strcmp(id,"slave_name")) e=snd_config_get_string(node,&slave); else if (strcmp(id,"comment") && strcmp(id,"type")) return -EINVAL; if (e<0) return e; } if (!path || path[0]!='/' || !slave) return -EINVAL; s=calloc(1,sizeof(*s)); if (!s) return -ENOMEM; s->path=strdup(path); if (!s->path || (e=snd_pcm_open_lconf(&s->slave,slave,stream,mode,root))<0) { free(s->path); free(s); return e<0?e:-ENOMEM; } s->io.version=SND_PCM_IOPLUG_VERSION; s->io.name="ALSAChain playback status"; s->io.callback=&callbacks; s->io.private_data=s; if ((e=snd_pcm_ioplug_create(&s->io,name,stream,mode))<0) goto fail; if ((e=snd_pcm_ioplug_set_param_list(&s->io,SND_PCM_IOPLUG_HW_ACCESS,1,&access))<0 || (e=snd_pcm_ioplug_set_param_list(&s->io,SND_PCM_IOPLUG_HW_FORMAT,5,formats))<0 || (e=snd_pcm_ioplug_set_param_minmax(&s->io,SND_PCM_IOPLUG_HW_CHANNELS,1,32))<0 || (e=snd_pcm_ioplug_set_param_minmax(&s->io,SND_PCM_IOPLUG_HW_RATE,4000,768000))<0) { snd_pcm_ioplug_delete(&s->io); return e; } *pcmp=s->io.pcm; return 0; fail: snd_pcm_close(s->slave); free(s->path); free(s); return e; }
SND_PCM_PLUGIN_SYMBOL(alsachain_status);
