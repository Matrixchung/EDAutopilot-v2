import configparser
import os
import re
def isFloat(str:str):
    pattern = re.compile(r'(.*)\.(.*)\.(.*)')
    if pattern.match(str):
        return False
    return str.replace(".", "").replace("-","").isdigit()
class Config:
    configPath = 'config.ini'
    defaultConfig = {
        "Main": {
            "debug": "False",
            "log_to_file": "True",
            "override_previous_logs": "False"
        },
        "GUI": {
            "load_default_on_startup": "False",
            "default_script": "",      # Default script path, the program will try to open it 
            "show_debug_window": "True"
        },
        "Image": {
            "game_resolution": [-1, -1],
            "calibrated_scale": [-1.0, -1.0],
        }
    }
    config = configparser.ConfigParser()
    def __init__(self,path=None,logger=None) -> None:
        if path: self.configPath = path 
        self.logger = logger
        if not os.path.exists(self.configPath): open(self.configPath,"w") # create empty config
        self.config.read(self.configPath, encoding='utf-8')
        rewrite = 0 # rewrite correct config
        ### check config consistency
        for key in self.defaultConfig:
            if key in self.config:
                data = self.defaultConfig[key]
                for value in data:
                    if value not in self.config[key]:
                        if self.logger: self.logger.warn(f"Missing value {value} in config section: [{key}]")
                        self.config[key][value] = str(data[value])
                        rewrite += 1
            else: 
                if self.logger: self.logger.warn(f"Missing section [{key}] in config")
                self.config[key] = self.defaultConfig[key]
                rewrite += 1
        if rewrite>0:
            self.save()
            if self.logger: self.logger.info(f"Successfully rewrote config with {rewrite} missing entries.")
        elif self.logger: self.logger.info(f"Loaded config: {self.configPath}")
    def get(self,key,value) -> object : 
        if key in self.config:
            if value in self.config[key]: 
                data:str = self.config[key][value] # here comes string data
                if data == '': return None
                if data.isdigit(): return int(data) # all digit
                if isFloat(data): return float(data) # float
                if data.lower() == 'true': return True
                if data.lower() == 'false': return False
                if '[' in data and ']' in data: # list
                    data = data.replace("[","").replace("]","").replace(" ","").split(",")
                    numericResult = []
                    for item in data:
                        if item.replace('-','').isdigit(): numericResult.append(int(item))
                        elif isFloat(item): numericResult.append(float(item))
                        else: 
                            numericResult = []
                            break # Not all elements are numbers
                    if len(numericResult)>0: return numericResult
                    return data # string list
                return data
        return None
    def set(self,key:str,value:str,data,save=True) -> None :
        self.config[key][value] = data
        if save: self.save()
    def save(self) -> None: 
        with open(self.configPath, "w") as dest:
            self.config.write(dest)

if __name__ == "__main__":
    config = Config()
    scale = config.get('Image','calibrated_scale')
