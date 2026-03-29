from django.core.cache import cache
import time
import logging

class BaseSecurityThrottle:
    scope = 'default'
    rate = '100/h'

    def parse_rate(self):
        num, period = self.rate.split('/')
        num_requests = int(num)
        
        duration = 3600
        if period.endswith('s'):
            duration = int(period[:-1]) if len(period) > 1 else 1
        elif period.endswith('m'):
            duration = int(period[:-1]) * 60 if len(period) > 1 else 60
        elif period.endswith('h'):
            duration = int(period[:-1]) * 3600 if len(period) > 1 else 3600
        elif period.endswith('d'):
            duration = int(period[:-1]) * 86400 if len(period) > 1 else 86400
        elif period == 'hour':
            duration = 3600
        elif period == 'minute':
            duration = 60
            
        return num_requests, duration

    def get_cache_key(self, request, view):
        ident = request.user.pk if request.user.is_authenticated else self.get_client_ip(request)
        return f'throttle_{self.scope}_{ident}'

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def allow_request(self, request, view):
        self.num_requests, self.duration = self.parse_rate()
        self.key = self.get_cache_key(request, view)
        self.history = cache.get(self.key, [])
        self.now = time.time()
        
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
            
        if len(self.history) >= self.num_requests:
            return False
            
        self.history.insert(0, self.now)
        cache.set(self.key, self.history, self.duration)
        return True

    def on_throttle_exceeded(self, request, view):
        logging.getLogger('octobox.security').warning(f"Red Flag: Rate Limit Exceeded para escopo {self.scope}. User={request.user.pk}")


class DataExfiltrationThrottle(BaseSecurityThrottle):
    scope = 'anti_exfiltration'
    rate = '60/5m'

class MassExportThrottle(BaseSecurityThrottle):
    scope = 'mass_export'
    rate = '2/1h'
