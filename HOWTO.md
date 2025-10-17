- [構建設置](#構建設置)
  - [步驟1：依序載入設置和參數覆寫](#步驟1依序載入設置和參數覆寫)
  - [步驟2：移除參數值](#步驟2移除參數值)
  - [步驟3：依物件參數預設值補全](#步驟3依物件參數預設值補全)
  - [步驟4：引用變數值（Interpolation）](#步驟4引用變數值interpolation)
    - [偵測循環依賴](#偵測循環依賴)
  - [步驟5：驗證設置](#步驟5驗證設置)
    - [驗證型別](#驗證型別)
    - [檢查不預期或缺失的參數](#檢查不預期或缺失的參數)
- [獲取幫助](#獲取幫助)
  - [檢視完整設置](#檢視完整設置)
  - [識別物件的參數](#識別物件的參數)
- [操作設置物件](#操作設置物件)
  - [存取與變更參數值](#存取與變更參數值)
- [實現物件](#實現物件)
  - [自動實現物件](#自動實現物件)
  - [手動實現物件](#手動實現物件)
  - [自動實現 instance method](#自動實現-instance-method)
  - [手動實現 instance method](#手動實現-instance-method)
  - [序列化設置](#序列化設置)
- [操控 list](#操控-list)
- [遍歷參數值](#遍歷參數值)
  - [手動遍歷](#手動遍歷)
  - [簡單遍歷](#簡單遍歷)
  - [複雜遍歷](#複雜遍歷)


# 構建設置

當需要從多個來源整合設置並確保參數正確性時，使用 SynConf 來構建完整的設置。透過初始化 `SynConfParser` 並呼叫 `parse_args()` 方法，即可獲得經過多階段處理的完整設置物件。

Given 初始化 `SynConf` parser 並解析命令列參數

```python
# main.py
parser = SynConfParser(...)
config = parser.parse_args()
```

When 執行解析

Then 得到經過下列步驟建構的設置 `config`：

## 步驟1：依序載入設置和參數覆寫

當需要靈活地組合多個來源的設置時，可以在命令列中交替使用 YAML 檔案和參數覆寫。系統會按照出現的順序依序處理，後面的設置會覆寫前面的設置。

Given 準備多個 YAML 檔案和參數覆寫

```yaml
# base.yaml
server: 
    port: 8080
    timeout: 30
exp:
    seed: 42
```

```yaml
# override.yaml
server:
    timeout: 10
    debug: true
```

When 交替使用檔案和參數覆寫

```bash
python main.py base.yaml exp.timeout=100 server.host=localhost override.yaml server.port=9090
```

Then 按順序依序應用每個設置，得到最終結果

```yaml
server:
    host: localhost    # 來自命令列參數覆寫
    port: 9090         # 來自 base.yaml -> 命令列參數覆寫
    timeout: 10        # 來自 base.yaml -> 命令列參數覆寫 -> override.yaml
    debug: true        # 來自 override.yaml
exp:
    seed: 100          # 來自 base.yaml
```

- 系統自動識別參數類型：帶有 `.yaml`、`.yml` 副檔名為 YAML 檔案，否則須是包含 `=` 的為參數覆寫
- **處理順序**：命令列中參數出現的順序處理，後面的設置覆蓋前面的設置
- **YAML 檔案覆寫**：以 YAML 檔案覆寫時會進行深度巢狀覆寫。而 list 類型的值會被直接取代而非合併
- **命令列參數覆寫**：使用 `.` 語法來表示巢狀 key 的路徑，使用 `=` 來指定參數的值。可以覆寫既有參數或新增新參數

## 步驟2：移除參數值

當需要從已合併的設置中移除特定參數時，使用 `REMOVE` 關鍵字。透過將參數值設定為 `REMOVE`，可以明確地從最終設置中刪除該參數，適合用於從預設設置中排除不需要的參數。

Given 準備基礎設置檔案

```yaml
# ./configs/default.yaml
server:
    host: localhost
    timeout: 10
    port: 9090
    debug: true
```

And 準備覆寫設置檔案來移除特定參數

```yaml
# ./config.yaml
server:
    debug: REMOVE                    # 明確移除 debug 參數
```

When 傳入多個檔案解析設置

```bash
python main.py configs/default.yaml config.yaml server.port=REMOVE
```

Then 得到移除指定參數後的設置

```yaml
server:
    host: localhost   # 來自 default.yaml
    timeout: 10       # 來自 default.yaml
    # port 參數已被移除
    # debug 參數已被移除
```

- 使用 `REMOVE` 可以明確地從設置中刪除參數
- 適合搭配多檔案合併來從預設設置中排除不需要的參數
- 可以與命令列參數搭配使用來動態移除參數

## 步驟3：依物件參數預設值補全

當需要確保設置記錄的完整性以便日後複現實驗時，系統會自動補全物件參數的預設值。透過檢查 `TYPE` 指定的物件定義，系統會將使用者未明確設定但具有預設值的參數自動加入設置中，避免因日後程式碼變更而影響實驗複現性。

Given 定義帶有預設參數的物件

```python
def func(act: str, message: str = "hello"): ...

class BaseModel:
    def __init__(self, learning_rate: float = 1e-4, batch_size: int = 32, **kwargs): 
        func(**kwargs)

class AwesomeModel:
    def __init__(self, loss_scale: float = 1.0, **kwargs):
        super().__init__(batch_size=16, **kwargs)
```

And 準備只設定部分參數的設置

```yaml
model:
    TYPE: awesome_package.model.AwesomeModel
    act: relu
    learning_rate: 1e-4
```

When 解析設置

Then 系統自動補全預設值，得到設置等同於
```yaml
model:
    TYPE: awesome_package.model.AwesomeModel
    act: relu            # 使用者設定的值
    learning_rate: 1e-4  # 使用者明確設定的參數不會被覆寫
    message: "hello"   # 自動補全的預設值
    # batch_size 非 AwesomeModel 可設定的參數
```

- 只有具有 `TYPE` 關鍵字的物件設置才會進行預設值補全
- 支援 class、function、instance method 和 class method

## 步驟4：引用變數值（Interpolation）

當需要在設置中引用其他參數的值或環境變數時，使用插值功能。SynConf 支援三種插值方式，系統會自動識別插值類型並進行相應處理：
- **參數插值** `((simple_name))`： 若只包含簡單的參數路徑，則代表引用配置中的該路徑的參數值，
- **環境變數插值** `((UPPER_CASE))`：若包含全大寫參數名，則引用環境變數
- **表達式插值** `((... `variable` ...))`：若包含以反引號包圍變數，則代表執行 Python 表達式的結果

Given 展示三種插值和遞迴引用的綜合範例

```yaml
dataset:
    num_classes: 10
model:
    # 參數插值（直接引用）
    output_features: ((dataset.num_classes))

    # 環境變數插值
    hidden_dim: ((FEATURE_SIZE))

    # 表達式插值
    dropout: ((int("`FEATURE_SIZE`"[1]) / `output_features`))
    
# 嵌入字串中使用 / 遞回引用
name: model_f=((model.output_features))_h=((model.hidden_dim))
```

And 設定環境變數

```bash
export FEATURE_SIZE=64
```

When 解析設置

Then 所有插值被遞迴解析為實際值

```python
{
    'dataset': {
        'num_classes': 10
    },
    'model': {
        'output_features': 10,          # 參數插值: dataset.num_classes
        'hidden_dim': 64,               # 環境變數插值 FEATURE_SIZE
        'dropout': 0.4,                 # 表達式插值: int("64"[1])/10
    },
    'name': 'model_f=10_h=64'           # 字串嵌入/遞迴引用 (引用的 model.output_features 引用了 dataset.num_classes)
}
```

### 偵測循環依賴

Given 插值形成循環引用
```yaml
# 錯誤範例：循環依賴
a: ((b))
b: ((c)) 
c: 3  
```
When 解析時有循環依賴
```bash
python main.py config.yaml c=((a)) # 形成 a → b → c → a 的循環
```
Then 顯示循環插值錯誤
```python
CircularInterpolationError: 

a: ((b))
→ b: ((c))
→ c: ((a))
→ a: ((b))
```


## 步驟5：驗證設置

當需要在執行前確保設置符合物件定義的要求時，使用驗證功能。透過在 `parse_args` 階段就檢查型別和參數是否正確，可以及早發現設置錯誤並避免執行時的問題。

### 驗證型別

當需要確保設置中的參數值符合物件定義的型別註解時，使用型別驗證功能。系統會根據物件的型別註解檢查每個參數值是否正確，並在發現錯誤時提供詳細的錯誤訊息。

Given 定義範例類別和函式

```python
class Parent:
    def __init__(
        self, 
        name: str,
        number: int | float = None, 
        vocab: None | list[float] = None,
        toy: Union[str, None] = None,
        dummy2: int = 5,
    ): ...

class Child(Parent):
    def __init__(
        self, 
        percent: float, 
        animal: Literal['cat', 'dog'] = 'dog', 
        dummy = 3, 
        name: Optional[str] = None,
        toy: Toy = None,
        stoy: SuperToy = None,
        toy_cls: Type[Toy] = None,
        stoy_cls: Type[SuperToy] = None,
        **kwargs
    ):
        super().__init__(name=name or "John", **kwargs)

class Toy: ...
class SuperToy(Toy): ...

def square(value: float) -> float: ...
```

And 初始化 `SynConfParser` 並指定 base_classes

```python
parser = SynConfParser(
    base_classes={
        'model': Parent,
        'model.stoy': SuperToy
    },
    validate_type=True, # 預設開啟
    validate_exclude=["model.dummy2"], # 不驗證這些參數
)
```

And 準備包含各種型別情況的設置

```yaml
model:
    TYPE: Child
    percent: 1                           # 錯誤：應該要是 float
    animal: pig                          # 錯誤：值應該是 'cat' 或 'dog'  
    dummy: false                         # 正確：無型別註解不檢查
    dummy2: "5"                          # 正確：型別錯誤或無法檢查，但被排除在檢查外
    toy:                                 # 正確：物件返回值符合型別
        TYPE: SuperToy
    stoy:
        TYPE: Toy                        # 錯誤：Toy 不是 SuperToy 子類別
    toy_cls: !!python/name:__main__.Toy  # 正確：使用 PyYAML 標籤傳入型別本身
    number:                              # 正確：函式返回值符合型別
        TYPE: square
        value: 0.3
    name: null                           # 正確：以子類別定義為準
    vocab: [a, b]                        # 正確：容器型別只檢查第一層
    stoy_cls:                            # 錯誤：期待型別而非實例
        TYPE: SuperToy
```

When 解析設置

Then 系統一次性報告所有參數驗證錯誤，包含型別錯誤等等。每段型別驗證類型的錯誤訊息包含錯誤原因、參數路徑、參數來源、實際值和其型別、期望的型別或值集合

```bash
ParameterValidationError: 

❌ Type mismatch
Parameter: model.percent
Expected: float
Actual: 1 (int)

❌ Type mismatch
Parameter: model.animal
Expected: Literal['cat', 'dog']
Actual: 'pig' (str)

❌ Type mismatch
Parameter: model.stoy
Expected: SuperToy
Actual: ... (Toy)

❌ Type mismatch
Parameter: model.stoy_cls
Expected: Type[SuperToy]
Actual: ... (SuperToy)
```

### 檢查不預期或缺失的參數

當需要確保設置包含物件所需的所有必要參數，且不包含無效參數時，使用參數對應性檢查。系統會比對設置與物件定義，檢查是否有拼寫錯誤的參數名稱或缺少必要的參數。

Given 物件定義

```python
class Parent:
    def __init__(self, c: int, d: float): ...
class Child(Parent):
    def __init__(self, a: int, b = 3, **kwargs):
        super().__init__(c = a + b, **kwargs)
def func(x: int): ...
```

And 初始化有啟用參數對應性檢查的 `SynConfParser`

```python
parser = SynConfParser(
    validate_mapping=True, # 預設開啟
    validate_exclude=["model.a"], # 排除不檢查的參數
) 
```

And 準備包含參數錯誤的設置

```yaml
model:
    TYPE: Child
    # 正確: 缺少必要參數 a，但被排除在檢查外
    # 正確: b 有預設值，可以省略
    # 錯誤: 缺少必要參數 d
    c: 5 # 錯誤: 物件不接受參數 c
    e: 7 # 錯誤: 物件不接受參數 e
fn:
    TYPE: func
    x: 3
    z: 5 # 錯誤: 物件不接受參數 z
```

When 解析設置

Then 系統一次性報告所有參數驗證錯誤，包含型別或對應性錯誤。每段參數對應性錯誤訊息格式範例如下
```bash
ParameterValidationError: 

❌ Missing parameters
Parameters: model.d
Object: Child

❌ Unexpected parameters
Parameters: model.c, model.e
Object: Child

❌ Unexpected parameters
Parameters: fn.z
Object: func
```

# 獲取幫助

## 檢視完整設置

當需要檢查複雜的設置建構過程是否正確，避免因設置錯誤而浪費執行時間時，使用設置檢視功能。透過 `--print` 參數，可以在程式執行前查看最終建構的完整設置，並需要手動確認後才繼續執行。

When 使用 `--print` 參數執行程式

```bash
python main.py config.yaml --print
```

Then 系統會以 YAML 形式，印出經過所有步驟處理後的最終完整設置內容，並提示按 Enter 鍵確認後才繼續執行程式

## 識別物件的參數

當需要了解某個物件可以接受哪些參數以及如何正確設置這些參數時，使用物件參數查詢功能。透過 `--help.object` 參數，可以獲得物件的完整參數資訊，包括可透過 `**kwargs` 間接定義的參數。

Given 物件間的 `**kwargs` 傳遞鏈

```python  
# ./objects.py
class BClass:
    def my_method(self, g: float):
        """
        Args:
            g: 猩猩
        """

def func(f: int = 5, **kwargs):
    """
    Args:
        f(int, optional): 狐狸。
    """
    b = BClass()
    b.my_method(**kwargs)

class AClass:
    @classmethod  
    def create(cls, e="hi", **kwargs) -> "AClass":
        func(**kwargs)
        ...

class Parent:
    def __init__(self, a, b: Literal["cat", "dog"], c, **kwargs):
        AClass.create(**kwargs)

class Child(Parent):
    def __init__(self, d, **kwargs):
        super().__init__(a=3, c=d*5, **kwargs)
```

When 查詢函式的參數

```bash
python main.py --help.object=objects.Child
```

Then 系統照著 `**kwargs` 傳遞鏈，印出所有可在查詢物件中設置的參數

```bash
objects.Child:
    d
→ objects.Parent: 
    b(Literal["cat", "dog"])
→ objects.AClass.create:
    e(default="hi")
→ objects.func:
    f(int, default=5): 狐狸
→ objects.BClass.my_method:
    g(float): 猩猩
```
- 支援 class、function、instance method、class method
- 遞迴追蹤 `**kwargs` 的參數傳遞
- 排除被呼叫者的已被呼叫者寫死設值的參數（如呼叫者 `Child` 的支援參數不包含被呼叫者 `Parent` 的 `a`、`c`）
- 排除物件本身參數（如 `self`、`cls`）

# 操作設置物件

## 存取與變更參數值

當需要在程式中讀取、修改或操作設置內容時，設置物件提供兩種存取方式。透過 dict 風格或 attribute 風格的語法，可以靈活地存取和操控巢狀的設置結構。

Given 已解析的設置物件

```python
config = parser.parse_args()  # 假設包含 model.learning_rate 等設置
```

When 使用 dict 風格存取

```python
value = config['model']['learning_rate'] # 取值
value = config['model'].get('learning_rate', 0.01)   # 預設值
config['model']['learning_rate'] = 0.01 # 設值
config['model'].pop('learning_rate') # 刪除
```

When 使用 attribute 風格存取

```python
value = config.model.learning_rate # 取值
value = getattr(config.model, 'learning_rate', 0.01) # 預設值
config.model.learning_rate = 0.01 # 設值
delattr(config.model, 'learning_rate') # 刪除
```

When 使用參數路徑存取

```python
config['model.learning_rate'] = 0.01  # 設值
value = config.get('model.learning_rate', 0.1)  # 取值
del config['model.learning_rate']  # 刪除
value = getattr(config, 'model.learning_rate', 0.01) # attribute 風格也適用
delattr(config, 'model.learning_rate') # 刪除
```

Then 兩種方式都能正確操作設置

- Dict 風格使用 `[]` 和字典方法，適合動態的 key 存取
- Attribute 風格使用 `.` 語法，程式碼更簡潔易讀
- 兩種風格可以混合使用，操作結果完全相同

# 實現物件

## 自動實現物件

當需要將設置中的物件定義轉換為實際的物件實例時，使用自動物件實現功能。透過 `realize` 方法，系統會遞迴地將所有帶有 `TYPE` 關鍵字的設置，轉換為對應的物件實例或函式返回值。

Given 定義相關的類別和函式

```python
class Optimizer:
    def __init__(self, lr): ...

class AwesomeModel:
    def __init__(self, hidden_size, optimizer: Optimizer): ...

def create_optimizer(lr) -> Optimizer: ...
```

And 準備包含巢狀物件的設置

```yaml
model:
    TYPE: AwesomeModel
    hidden_size: 64
    optimizer: 
        TYPE: create_optimizer    # 巢狀物件定義
        lr: 0.01
```

When 自動實現所有物件

```python
realized_config = config.realize()
```

Then 得到完全實例化的物件

```python
{
    'model': AwesomeModel(
        hidden_size=64, 
        optimizer=create_optimizer(lr=0.01)  # 子物件也被實例化
    )
}
```

When 實現某設置下的所有物件，並覆蓋部分參數

```python
model = config.model.realize(overwrites={'optimizer.lr': 0.02})
```

Then 得到覆蓋參數後的實例

```python
# 等同於
model = AwesomeModel(
    hidden_size=64,
    optimizer=create_optimizer(lr=0.02)  # 使用覆蓋的學習率
)
```

- 遞迴處理所有巢狀的 `TYPE` 定義，由深至淺實例化
- 使用 `overwrites` 參數可以動態覆蓋任何巢狀參數
- 不使用 `TYPE` 關鍵字的物件會保持原始字典形式

## 手動實現物件

當需要更精確地控制物件實例化過程，或進行複雜的初始化邏輯時，使用手動物件實現功能。透過 `resolve_type` 方法獲取物件類型，再用 `kwargs` 方法獲取純淨的參數字典，可以分離並明確地控制物件的實例化過程。

Given 準備簡單的物件設置

```yaml
model:
    TYPE: AwesomeModel
    hidden_size: 64
    # 不包含需要遞迴實例化的子物件
```

When 手動實例化物件

```python
cls = config.model.resolve_type()  # 獲取 AwesomeModel 類別
model = cls(**config.model.kwargs)  # 傳入參數並實例化
```

Then 得到實例化的物件

```python
# 等同於
model = AwesomeModel(hidden_size=64)
```

- `resolve_type` 方法返回 `TYPE` 指定的實際物件（類別、函式等）
- `kwargs` 方法會過濾掉 `TYPE` 等特殊關鍵字，返回純淨的參數字典
- 適合用於需要複雜初始化邏輯或更清晰控制流程的場景
- 提供比自動實現更明確且靈活的控制

## 自動實現 instance method

當需要執行某個物件的 instance method 並獲取其返回值時，使用 instance method 實現功能。透過 method 本身 `self` 參數指定實例的設置，系統的遞迴性物件實現自然會先創建物件實例，再呼叫指定的方法並返回結果。

Given 定義包含 instance method 的類別

```python
class Experiment:
    def __init__(self, seed: int = 0):
        self.seed = seed
    
    def cross_validate(self, folds: int) -> dict[str, float]:
        return {'F1': 0.9, 'Precision': 0.95}
```

And 準備 instance method 的設置

```yaml
TYPE: Experiment.cross_validate
folds: 5
self:                # 指定創建實例所需的參數
    TYPE: Experiment
    seed: 1
```

When 自動實現 instance method

```python
metrics = config.realize()
```

Then 得到方法執行的返回值

```python
metrics == {'F1': 0.9, 'Precision': 0.95}
```

## 手動實現 instance method

當需要更精確地控制 instance method 的呼叫過程，或進行複雜的實例初始化時，使用手動 instance method 實現功能。透過先手動創建實例，再用 `resolve_type` 獲取方法並手動呼叫，可以實現最大的靈活性和控制力。

Given 定義需要複雜初始化的類別

```python
class DataProcessor:
    def __init__(self, complex_data: Any): 
        self.num_classes = 3
    
    def get_num_targets(self, batch_size: int) -> int:
        return self.num_classes * batch_size
```

And 準備 instance method 的設置

```yaml
processor_task:
    TYPE: DataProcessor.get_num_targets
    batch_size: 32
```

When 手動創建實例並呼叫方法

```python
# 手動創建並控制實例化過程
processor = DataProcessor(complex_data=None) # 可能是很複雜的資料

# 獲取方法並手動呼叫
method = config.processor_task.resolve_type()  # 獲取 get_num_targets 方法
result = method(processor, **config.processor_task.kwargs)  # 傳入實例和參數
```

Then 得到使用指定實例執行的方法結果

```python
result == 96
```

## 序列化設置

當需要將複雜的巢狀設置轉換為扁平化的格式以便記錄或展示時，使用序列化功能。透過 `pretty` 方法，可以獲得美觀且易讀的扁平化字典，並可選擇性地排除特定參數。

Given 準備包含巢狀結構的設置

```python
config = {
    'model': {
        'TYPE': 'AwesomeModel',  # 物件類型
        'hidden_size': 64
    },
    'dataset': {
        'batch_size': 32
    }
}
```

When 序列化為扁平化格式

```python
pretty_config = config.pretty()
```

Then 得到扁平化的美觀字典

```python
{
    "model.TYPE": "AwesomeModel",    # 巢狀 key 用 . 分隔
    "model.hidden_size": 64,
    "dataset.batch_size": 32
}
```

When 排除特定參數進行序列化

```python
pretty_config = config.pretty(exclude=['dataset.batch_size'])
```

Then 得到排除指定參數的結果

```python
{
    "model.TYPE": "AwesomeModel", 
    "model.hidden_size": 64
    # dataset.batch_size 被排除
}
```

- 巢狀的 key 會用 `.` 連接成扁平化的 key
- 物件實例會被轉換回其類別名稱字串
- 可透過 `exclude` 參數排除不需要的參數
- 適合用於實驗記錄和設置展示

# 操控 list

當需要以更靈活的方式管理 list 元素，如新增、刪除或替換特定項目時，使用 `LIST` 類型。透過將 `TYPE` 設定為 `LIST`，可以用 dict 的語法來操作 list 元素，最終仍會得到標準的 list 結構。

Given 準備基礎的 list 設置

```yaml
# ./configs/default.yaml
callbacks:
    TYPE: LIST
    log: log_callback           # 使用有意義的 key 名稱
    ckpt: save_model_callback
    debug: debug_callback
```

And 準備覆寫設置來修改 list 內容

```yaml
# ./config.yaml
callbacks:
    TYPE: LIST
    ckpt: REMOVE                    # 移除特定項目
    stop: early_stopping_callback   # 新增項目
```

When 傳入多個檔案解析設置

```bash
python main.py configs/default.yaml config.yaml
```

Then 得到修改後的 list

```yaml
callbacks:
    - log_callback             # 保留的項目
    - debug_callback           # 保留的項目
    - early_stopping_callback  # 新增的項目
    # save_model_callback 被移除
```

- 使用 `TYPE: LIST` 來啟用 dict 風格的 list 操作
- 可以用有意義的 key 名稱來標識 list 元素
- 支援 `REMOVE` 來刪除特定元素，搭配多檔案合併使用
- 最終輸出仍為標準的 list 格式

# 遍歷參數值

當需要在相同的設置邏輯下測試不同的參數組合時，使用參數遍歷功能。透過程式化的方式產生多組設置，可以在保持所有插值和合併邏輯的同時，系統性地探索不同的參數值。

## 手動遍歷

當需要完全自定義遍歷邏輯，包含複雜的條件判斷時，使用手動方式。透過使用者在程式中迴圈呼叫 `parse_args` 時加入覆蓋參數，可以實現任意複雜的遍歷模式。

Given 準備包含插值邏輯的設置檔

```yaml
# config.yaml
dataset: imagenet
devices: [1, 2]
batch_size_per_device: ((`batch_size`//len(`devices`)))  # 動態計算
```

And 在程式中定義遍歷邏輯

```python
# main.py
parser = SynConfParser()
for dataset in ['iris', 'cifar10']:
    for batch_size in [32, 64]:
        if dataset == 'iris' and batch_size == 32:
            continue  # 跳過特定組合
        config = parser.parse_args(
            sys.argv[1:] + [f"dataset={dataset}", f"batch_size={batch_size}"]
        )
        # 使用 config 進行實驗...
```

When 執行遍歷

```bash
python main.py config.yaml
```

Then 依序得到不同的設置組合

第一次迴圈：
```yaml
dataset: iris
devices: [1, 2] 
batch_size_per_device: 32    # 64//2 的結果
batch_size: 64
```

第二次迴圈：
```yaml
dataset: cifar10
devices: [1, 2]
batch_size_per_device: 16    # 32//2 的結果
batch_size: 32
```

第三次迴圈：
```yaml
dataset: cifar10
devices: [1, 2]
batch_size_per_device: 32    # 64//2 的結果
batch_size: 64
```

- 完全自定義遍歷邏輯和條件判斷
- 保持所有設置建構邏輯（合併、插值等）
- 適合複雜的參數組合篩選需求

## 簡單遍歷

當需要對單個或多個參數進行笛卡爾積遍歷時，使用簡單遍歷功能。透過 `--sweep` 參數搭配 `key=<YAML list>` 格式，可以直接指定各個參數的候選值，系統會自動產生所有可能的組合。

Given 準備處理遍歷結果的程式

```python
# sweep.py
parser = SynConfParser()
configs = parser.parse_args()

if isinstance(configs, list):    # 有 --sweep 時返回 list
    for config in configs:
        experiment = config.exp.realize()
        experiment.run(**config.run.kwargs)
else:                           # 無 --sweep 時返回單一 config
    experiment = configs.exp.realize()
    experiment.run(**configs.run.kwargs)
```

When 使用 `--sweep` 搭配參數候選值

```bash
python sweep.py config.yaml --sweep log.name=[my_((exp.seed)), REMOVE, hello] exp.seed=[0, 1, 2]
```

Then 系統產生所有參數組合並依序執行

等同於下列巢狀迴圈：
```python
for log_name in ['my_((exp.seed))', 'REMOVE', 'hello']: # 前面的參數為外層迴圈
    for exp_seed in [0, 1, 2]:                         # 後面的參數為內層迴圈
        config = parser.parse_args([
            "config.yaml",
            f"log.name={log_name}",
            f"exp.seed={exp_seed}"
        ])
        experiment = config.exp.realize()
        experiment.run(**config.run.kwargs)
```

- 使用 `--sweep key=<YAML list>` 語法指定參數和候選值。`<YAML list>` 為表示 list 的 YAML 字串
- 可以同時指定多個參數，進行笛卡爾積組合
- 參數順序決定遍歷的巢狀順序（前面的參數為外層迴圈）
- 當使用 `--sweep` 時，`parse_args` 返回設置列表而非單一設置

## 複雜遍歷

當需要實現複雜的參數組合邏輯，如某些參數必須同時出現或互斥時，使用複雜遍歷功能。透過 `--sweep` 參數指定自定義生成函式，可以精確控制哪些參數組合需要被測試。

Given 定義自定義的參數組合生成函式

```python
# ./mysweep.py
def my_sweep() -> Iterator[dict[str, Any]]:
    for model_batch_size in [2, 4, 6]:
        for exp_seed, name in [(0, 'first'), (1, 'second'), (2, 'third')]:
            if model_batch_size == 2 and exp_seed == 0:
                continue  # 跳過特定組合
            yield {
                "model.batch_size": model_batch_size,
                "exp.seed": exp_seed,
                "log.name": name
            }
```

When 使用自定義函式進行遍歷

```bash
python sweep.py config.yaml --sweep mysweep.my_sweep
```

Then 系統按照自定義邏輯產生參數組合

等同於執行：
```python
for model_batch_size in [2, 4, 6]:
    for exp_seed, name in [(0, 'first'), (1, 'second'), (2, 'third')]:
        if model_batch_size == 2 and exp_seed == 0:
            continue  # 跳過特定組合
        
        config = parser.parse_args([
            "config.yaml",
            f"model.batch_size={model_batch_size}",
            f"exp.seed={exp_seed}",
            f"log.name={name}"
        ])
        experiment = config.exp.realize()
        experiment.run(**config.run.kwargs)
```

- 使用 `--sweep FUNCTION_PATH` 指定自定義的生成函式
- 系統自動識別：如果 `--sweep` 後的參數只有一個且不包含 `=` 則為複雜遍歷的函式路徑
- 生成函式應該 yield 包含參數覆寫的字典
- 支援任意複雜的條件邏輯和參數依賴關係
- 適合需要精細控制參數組合的進階應用場景