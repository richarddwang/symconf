- [Construct configuration](#construct-configuration)
    - [1. Read YAML and dotenv files](#1-read-yaml-and-dotenv-files)
    - [2. MERGE configuration](#2-merge-configuration)
    - [3. Command line arguments](#3-command-line-arguments)
    - [4. Remove argument value](#4-remove-argument-value)
    - [5. Default argument value of object](#5-default-argument-value-of-object)
    - [6. Variable Interpolation](#6-variable-interpolation)
    - [7. Expression Interpolation](#7-expression-interpolation)
- [Validation](#validation)
    - [Validate type](#validate-type)
    - [Check unexpected/missing arguments](#check-unexpectedmissing-arguments)
- [Help](#help)
    - [Inspect full configuration](#inspect-full-configuration)
    - [Identify object's arguments](#identify-objects-arguments)
- [Configuration Object](#configuration-object)
    - [Access & Manipulation](#access--manipulation)
    - [Automatically realize object](#automatically-realize-object)
    - [Manually realize object](#manually-realize-object)
    - [Realize instance method](#realize-instance-method)
    - [Serialization](#serialization)
- [List manipulation](#list-manipulation)
- [Sweep over values](#sweep-over-values)
    - [Hard code](#hard-code)
    - [Simple sweep](#simple-sweep)
    - [Complex sweep](#complex-sweep)

# Construct configuration

- Given: 初始化 `SymConf` parser 並解析命令列參數
    ```python
    # main.py
    parser = SymConfParser(...)
    config = parser.parse_args()
    ```

執行時 SymConf 會依序執行下列階段建構，最終得出設置 `config` 
1. 讀取 YAML 和 dotenv 檔案
2. MERGE 設置
3. 命令列參數
4. 物件初始化的參數預設值
5. Variable Interpolation
6. Expression Interpolation

## 1. Read YAML and dotenv files

讀取並合併多個 YAML 檔案，另外還可以匯入 dotenv 檔案的環境變數

- 說明:
    - 透過 CLI positional arguments 來讀取一或多個 YAML 檔案
    - 使用內建的 `--env` 來讀取一或多個 dotenv 檔案匯入環境變數
    - 多個檔案時會深度合併 (nested merging)，越後面的檔案優先度越高
    - 注意 list 在合併時會被直接整個取代而非合併或延伸
- 範例：
    - Given: 一或多個 YAML 檔案
        ```yaml
        # config1.yaml
        server: 
            host: localhost
            ports: 
                - 8080
                - 8081
        ```
        ```yaml
        # config2.yaml
        server:
            timeout: 10
            ports:
                - 9090
        ```
    - When: `python main.py config1.yaml config2.yaml`
    - Then: 得到 `config` 等同
        ```yaml
        server:
            host: localhost
            timeout: 10
            ports:
                - 9090
        ```
        - 注意 list 被直接取代了


## 2. MERGE configuration

疊加 YAML 檔案雖然方便，但也可能造成難以理解參數間的覆寫關係。SymConf 能在 YAML 裡直接引用別的 YAML 的設置。

說明：
- 使用 `MERGE` 關鍵字來引用其他 YAML 檔案的設置並深度合併
- `MERGE` 的值可以是 YAML 檔案的相對路徑或絕對路徑，還可以加上 nested key

範例：
- Given: 
    ```yaml
    # ./configs/setting1.yaml
    server:
        timeout: 10
        port: 9090
    
    ```
    ```yaml
    # ./configs/setting1.yaml
    more_level:
        server2:
            port: 7070
            host: awesome.com
    ```
    ```yaml
    # ./config.yaml
    MERGE: configs/default
    server:
        host: localhost
        MERGE: configs/setting1.more_level.server2
        port: 8080
    ```
- When: `python main.py config.yaml`
- Then: 得到 `config` 等同
    ```yaml
    server:
        timeout: 10
        port: 8080
        host: awesome.com
    ```
    由上往下執行，因此後面的值在深度合併裡會覆寫前面的值

## 3. Command line arguments

在 CLI 覆寫設置，避免直接更動 YAML 檔案

說明：
- 透過 `--args` 傳入欲覆寫的參數和值
- 以 "." 表示 nested key、 "=" 指定值，來表示覆寫的參數和值
- 多個覆寫參數時，後面的參數優先度較高

範例：
- Given: YAML 檔案
    ```yaml
    exp:
        seed: 42
    ```
- When: `python main.py [YAML_FILE...] --args exp.seed=3 exp.name=hi`
- Then: 得到 `config` 等同
    ```yaml
    exp:
        seed: 3
        name: hi
    ```

## 4. Remove argument value

使用 `REMOVE` 關鍵字來刪除某參數

範例：
- Given: 
    ```yaml
    # ./configs/servers/default.yaml
    server:
        timeout: 10
        port: 9090
    ```
    ```yaml
    # ./config.yaml
    server:
        MERGE: servers.default.server
        timeout: REMOVE
    ```
- When: `python main.py config.yaml`
- Then: 得到 `config` 等同
    ```yaml
    server:
        port: 9090
    ```

## 5. Default argument value imputation

保證在記錄設置時的完整性，即使在之後物件參數的預設值改變，也不會導致無法使用之前記錄的設置複現。

說明：
- 當某設置是針對某物件，且該物件初始化的某參數使用者沒有設定時，且該物件初始化參數有預設值時，自動將設置中該參數設定為預設值
- 使用 `TYPE` 關鍵字和物件路徑來指定物件，物件可以是 class, function, instance method, or class method

範例：
- Given: 某設置是針對某物件
    ```yaml
    model:
        TYPE: awesome_package.model.AwesomeModel
        learning_rate: 1e-3
    ```
- And: 該物件的初始化有預設參數值
    ```python
    class AwesomeModel
        def __init__(self, learning_rate: float = 1e-4, batch_size=32):
    ```
- When: 讀取設置後
- Then: 得到設置等同於
    ```python
    {'model': 
        {
            'TYPE': awesome_package.model.AwesomeModel,
            'learning_rate': 1e-3,
            'batch_size': 32 
        }
    }
    ```

## 6. Variable Interpolation

如同 Python f-string 般的功能

說明：
- 使用 `${}` 包住參數名稱來表示 variable interpolation
- 可以單獨使用變數，也可以將變數夾雜於值中
- 參數名稱也可以是環境變數。若無法在設置中找到該變數名，就會從環境變數中找

範例：
- Given: YAML 檔如
    ```yaml
    output_features: ${dataset.num_classes} 
    name: n=${dataset.num_classes}
    dummy: 1${dataset.num_classes} 
    dataset:
        num_classes: ${NUM_CLASSES}
    ```
- And: 環境變數 `NUM_CLASSES` 為 10
- When: 讀取該 YAML 檔設置
- Then: 等同於 placeholders 被替換成相應的值
    ```python
    {
        'output_features': 10,
        'name': 'n=10',
        'dummy': 110,
        'dataset': {'num_classes': 10},
    }
    ```

## 7. Expression Interpolation

透過 Python 表達式來動態表達參數值

說明：
- 當在`${}` 裡出現 ` `` `，則 ` `` ` 包住的是變數名，且 "${}" 包住的是 Python 表達式

範例：
- Given: YAML 檔如
    ```yaml
    dataset:
        num_classes: 10
    model: 
        output_features: ${`dataset.num_classes` + `model.extra_outputs`} 
        extra_outputs: 2
    ```
- When: 讀取該 YAML
- Then: 替換成表達式的結果。等同於
    ```yaml
    dataset:
        num_classes: 10
    model: 
        output_features: 12 
        extra_outputs: 2
    ```

# Validation

在 `parse_args` 就檢查設置是否符合物件要求

- Given:
    ```python
    class Parent:
        def __init__(
            self, 
            name: str,
            number: int | float = None, 
            vocab: None | list[float] = None,
            toy: Union[str, None] = None,
        ): ...
    
    class Child:
        def __init__(
            self, 
            percent: float, 
            animal: Literal['cat', 'dog'] = 'dog', 
            dummy = 3, 
            name: Optional[str] = None,
            toy: Toy = None,
            stoy: SuperToy = None,
            toy_cls: Type[Toy] = None,
            **kwargs
        ):
            super().__init__(name=name or "John", **kwargs)

    class Toy: ...

    class SuperToy(Toy): ...

    def square(value: float) -> float: ...
    ```

以下的每個檢查在 `SymConfParser` 初始化時都可以選擇性關閉，但預設為開啟

## Validate type

規則：
- 參數值必須符合其型別註解 
- 若參數無型別註解則不檢查
- 參數型別若是 container，則只檢查第一層的型別
- 若參數值設為物件設置，則以該物件的返回值檢查是否符合參數型別
- 若參數值設為物件設置且帶有標籤 `!!base_class:xxx`，則該物件的 `TYPE` 後的類別必須是屬於 `xxx` 類別（同類別或其子類別）

範例：
- Given: 初始化 `SymConfParser` 時指定了 key 的 base_classes
    ```python
    parser = SymConfParser(
        base_classes={
            'model': Parent,
            'model.stoy': SuperToy
        },
    )
    ```
- And: 設置
    ```yaml
    model:
        TYPE: Child
        percent: 1 # 報錯。 應該要是 float
        animal: pig # 報錯。值應該是 'cat' 或 'dog'
        dummy: false # 不報錯。無型別註解不檢查
        toy: # 不報錯。其類別初始化的返回值屬於型別提示中的類別
            TYPE: SuperToy
        stoy:
            TYPE: Toy # 報錯。Toy 不是 SuperToy 或其子類別
        toy_cls: !!python/name:__main__.Toy # 若要傳入類別的型別本身而非其實體，則可使用 pyyaml built-in tag
        number: # 不報錯。該函式的返回值屬於型別提示中的類別
            TYPE: square
            value: 0.3
        name: null # 不報錯。相同參數只看最子類別的定義
        vocab: [a, b] # 不報錯。因為當型別是 container 時只檢查第一層型別
    ```
- When: 讀取設置
- Then: 會一次性報所有的錯，且
    每行錯誤訊息會包含以下資訊：物件名、參數名、期待的型別、實際的型別、實際的參數值

## Check unexpected/missing arguments

- Given: 設置
    ```yaml
    model:
        TYPE: Child
        parcent: 0.1 # 報錯。不預期參數 parcent
        # 報錯， 預期要有 percent 參數
        # 不會報錯沒有 name 參數，因為 name 的定義是看最子類別 Child 的定義
    ```
- When: 讀取設置
- Then: 一次性報所有的錯。每行錯誤訊息會包含以下資訊：物件名、參數名、錯誤類型(缺少/不預期)

# Help

## Inspect full configuration

為了避免複雜的設置建構過程中出錯，SymConf 提供 `--print` 來印出最終建構的設置，並要求使用者按 Enter 確認後才會執行

```bash
python main.py ... --print
```

## Identify object's arguments

了解某物件可設置的參數和如何設置

說明：
- 使用 `--help.object OBJECT_PATH`
- 物件可以是 class, function, instance method, or class method
- `**kwargs` 追蹤
    - 當物件參數有 `**kwargs`，且在函式內部以 `**kwargs` 展開作為其他物件的參數時，SymConf 能辨認出其他物件的參數也屬於該物件的參數。
    - 對 `**kwargs` 的追蹤為遞迴，且不限呼叫與被呼叫物件種類是否相同
    - 若在函式主體中 `**kwargs` 被使用多次，則只追蹤第一次展開的物件的參數
    - 若是用在多重繼承的親類別初始化中，則僅會追蹤第一順位的親類別
- 顯示
    - 參數來源物件路徑
    - 參數名稱
    - 參數型別 (若有型別註解)
    - 預設值 (若有預設值)
    - 參數說明 (若有 docstring 且有在 Args 區塊中說明該參數)

範例：

- Given: 物件定義
    ```python
    # ./definition.py
    class Parent:
        def __init__(self, a: int, b: str, c: bool = True):
            """
            Args:
                a: 蘋果
                b: 香蕉
                c: 車子
            """

    class Child(Parent):
        def __init__(self, d: float, **kwargs):
            """
            Args:
                d: 鴨子
            """
            super().__init__(3, b=d + 4, **kwargs)
    ```
- When: 給定物件路徑 `python main.py --help.object=definition.Child`
- Then: SymConf 會 import 該物件，並印出該物件的參數
    ```
    For `definition.Child`:
        d(float): 鴨子
    For `definition.Parent`:
        c(bool, default=True): 車子
    ```
    - 不包含參數 a, b ，因為它們在 Child 裡面被手動設值了
    - 包含參數 c ，因為它有預設值，且 Child 裡面沒有手動設值
    - 不包含參數 self 不會出現在列表中

- Given:
    ```python
    # ./objects.py
    class BClass:
        def my_method(self, *args, f: float): 
            """
            Args:
                f(int): 狐狸
            """

    class AClass:
        @classmethod
        def create(cls, e, **kwargs) -> "AClass":
            b = BClass()
            b.my_method(5, **kwargs)

    class MyClass:
        def __init__(self, a, b: bool, c, **kwargs):
            AClass.create(**kwargs)

    def func(d, **kwargs):
        MyClass(3, c = d * 5, **kwargs)
    ```
- When: 給定物件路徑 `python main.py --help.object objects.func`
- Then: 印出
    ```
    For `objects.func`:
        d
    For `objects.MyClass`:
        b(bool)
    For `objects.AClass`:
        e
    For `objects.BClass`:
        f(float): 狐狸
    ```
    此例中可辨認出 `func` 的參數為 d, b, e, f。沒有 a, c 是因為其已在 `func` 裡面被手動設值。沒有 cls 和 self 是因為不包含物件本身。

# Configuration Object

## Access & Manipulation

Dict style:
- 取值：`config['model']['learning_rate']`
- 預設值：`config['model'].get('learning_rate', 0.01)`
- 設值：`config['model']['learning_rate'] = 0.01`
- 刪除：`config['model'].pop('learning_rate')`

Attribute style:
- 取值：`config.model.learning_rate`
- 預設值：`getattr(config.model, 'learning_rate', 0.01)`
- 設值：`config.model.learning_rate = 0.01`
- 刪除：`delattr(config.model, 'learning_rate')`

## Automatically realize object

用 `realize` 方法將物件路徑和參數轉成實例或函式返回值

遞迴由深至淺地，將任何帶有 `TYPE` 的設置值轉成物件實例或函式返回值

- Given: 設置 `config` 等同於
    ```yaml
    model:
        TYPE: AwesomeModel
        hidden_size: 64
        optimizer: 
            TYPE: create_optimizer
            lr: 0.01
    ```
- And: 物件定義
    ```python
    class Optimizer:
        def __init__(self, lr): ...

    class AwesomeModel:
        def __init__(self, hidden_size, optimizer: Optimizer): ...
    
    def create_optimizer(lr) -> Optimizer: ...
    ```
- When: `realized_config = config.realize()`
- Then: 得到的 `realized_config` 等同於
    ```python
    {
        'model': AwesomeModel(
            hidden_size=64, 
            optimizer=create_optimizer(lr=0.01),
        )
    }
    ```

若想要在解析物件時，手動傳入參數覆蓋原參數，可以使用 `realize` 的 `overwrites` 參數。另外，我們也可以選擇實現只有該物件的設置，則回直接回傳實例或函式返回值。

- When: 呼叫 `realize` 時指定欲覆蓋的參數的 nested key 和值
    ```python
    model: AwesomeModel = config.model.realize(overwrites={'optimizer.lr': 0.02})
    ```
- Then: 得到 `AwesomeModel` 實例，如同
    ```python
    model = AwesomeModel(
        hidden_size=64,
        optimizer=create_optimizer(lr=0.02),
    )

若不想要初始化子物件，則不要在該子物件處使用 `TYPE` 標籤，可以使用 pyyaml built-in tag 指定類別。例如

- Given:
    ```yaml
    model:
        TYPE: AwesomeModel
        hidden_size: 64
        optimizer: 
            creator: !!python/name:<module_path>.create_optimizer
            lr: 0.001
    ```
- When: `config.model.realize()`
- Then: 在初始化 `AwesomeModel` 時，會將 `config.model.optimizer` 以原始形式代入`optimizer` 參數

## Manually realize object

若物件類型（`TYPE`）是靜態的，且不需要遞迴初始化子物件時，為避免自動物件實現難以理解，也可以手動初始化物件

説明：
- 透過設置物件的 `kwargs` 方法來取得該物件不包含特殊關鍵字的參數字典

範例：
- Given: 設置 `config` 等同於
    ```yaml
    model:
        TYPE: AwesomeModel
        hidden_size: 64
    ```
- When: `model = AwesomeModel(**config.model.kwargs)`
- Then: 等同於
    ```python
    model = AwesomeModel(hidden_size=64)
    ```

## Realize instance method



自動實現 instance method 並返回值。需要在該 method 設置下，以 關鍵字 `CLASS` 描述其 class 的設置

- Given:
    ```python
    class Experiment:
        def __init__(self, seed: int):
            self.seed = seed
        
        def cross_validate(self, folds: int) -> dict[str, float]:
            return {'F1': 0.9, 'Precision': 0.95}
    ```
- And:
    ```yaml
    TYPE: Experiment.cross_validate
    folds: 5
    CLASS:
        seed: 1
    ```
- When: `metrics = config.realize()`
- Then: `metrics == {'F1': 0.9, 'Precision': 0.95}`

當然也可以手動實現

- Given:
    ```yaml
    method:
        TYPE: Experiment.cross_validate
        folds: 5
    exp:
        seed: 1
    ```
- When: `metrics = Experiment(**config.exp.kwargs).cross_validate(**config.method.kwargs)`
- Then: `metrics == {'F1': 0.9, 'Precision': 0.95}`

## Serialization

方便記錄美觀

説明：
- 設置物件的 `pretty` 方法來取得美觀的字典
- 扁平化巢狀設置
- 可以排除指定的參數
- 將實現的物件實例轉回物件型別名

範例：
- Given: 設置 `config` 等同於
    ```python
    {
        'model': {
            'TYPE': AwesomeModel,
            'hidden_size': 64
        },
        'dataset': {
            'batch_size': 32
        }
    }
    ```
- When: `config.pretty()`
- Then: 回傳的字典應該是
    ```python
    {
        "model.TYPE": "AwesomeModel",
        "model.hidden_size": 64,
        "dataset.batch_size": 32
    }
    ```
- When:  `config.pretty(exclude=['dataset.batch_size'])`
- Then: 回傳的字典應該是
    ```python
    {
        "model.TYPE": "AwesomeModel",
        "model.hidden_size": 64
    }
    ```

# List manipulation

SymConf 提供 `LIST` 為一個特殊的 `TYPE` 值，來以 dict 的方式修改 list 的元素

- Given: 設置
    ```yaml
    # configs/default.yaml
    callbacks:
        TYPE: LIST
        log: log_callback
        ckpt: save_model_callback
    ```
    ```yaml
    # config.yaml
    callbacks:
        MERGE: default.callbacks
        ckpt: DELETE
        stop: early_stopping_callback
    ```
- When: 設定設置庫為 `configs` 的 `SymConfParser` 讀取 `config.yaml`
- Then: 得到設置如同
    ```yaml
    callbacks:
        - log_callback
        - early_stopping_callback
    ```
    利用了 dict-style 方式來修改，但最後還是得到了 list

# Sweep over values

在保持設置建構邏輯的情況下，得到不同參數組合的設置

## Hard code

迴圈呼叫 `parse_args`，並用 `--args` 在每次迴圈中覆蓋想要改變的參數

- Given: 有做某些 interpolation 的設置檔
    ```yaml
    # config.yaml
    dataset: imagenet
    devices: [1, 2]
    batch_size_per_device: ${`batch_size`//len(`devices`)}
    ```
- And:  
    ```python
    # main.py
    parser = SymConfParser()
    for dataset in ['iris', 'cifar10']:
        for batch_size in [32, 64]:
            if dataset == 'iris' and batch_size == 32:
                continue
            config = parser.parse_args(sys.argv[1:] + ["--args"] + [f"dataset={dataset}", f"batch_size={batch_size}"])
    ```
- When: `python main.py config.yaml --args dataset=dummy`
- Then: 每個 loop 依序得到 `config` 如同
    ```yaml
    dataset: iris
    devices: [1, 2]
    batch_size_per_device: 16
    batch_size: 32
    ```
    ```yaml
    dataset: cifar10
    devices: [1, 2]
    batch_size_per_device: 16
    batch_size: 32
    ```
    ```yaml
    dataset: cifar10
    devices: [1, 2]
    batch_size_per_device: 32
    batch_size: 64
    ```

## Simple sweep

當只有一個參數需要 sweep ，或可以用 `product` 表示多個參數的 sweep 時

說明：
- `--sweep KEY=VAL1,VAL2,...` 其中 KEY 為參數的 nested key，VAL 為該參數的搜尋值
- `--sweep` 後可描述多個參數和其搜尋值，越前面的參數等同於越外層的迴圈
- 當有 `--sweep` 時，`parse_args` 回傳 list of configs，每次會得到不同參數組合的設置

範例：
- Given: 
    ```python
    # sweep.py
    parser = SymConfParser()
    config = parser.parse_args()
    if isinstance(config, list):
        for config in configs:
            experiment = config.exp.realize()
            experiment.run(**config.run.kwargs)
    else:
        experiment = config.exp.realize()
        experiment.run(**config.run.kwargs)
    ```
- When: `python sweep.py ... --sweep model.batch_size=2,4,6 exp.seed=0,1,2`
- Then: 等同於
    ```python
    for model_batch_size in [2, 4, 6]:
        for exp_seed in [0, 1, 2]:
            config = parser.parse_args(sys.argv[1:] + [
                "--args",
                f"model.batch_size={model_batch_size}",
                f"exp.seed={exp_seed}",
            ])
            experiment = config.exp.realize()
            experiment.run(**config.run.kwargs)
    ```

## Complex sweep

當有複雜邏輯譬如多個參數有些要一起出現或不能一起出現時

說明：
- `--sweep FUNCTION_PATH` 來指定一個生成不同設置覆寫的函式

範例：
- Given: 函式定義
    ```python
    # ./mysweep.py
    def my_sweep()-> dict[str, Any]:
        for model_batch_size in [2, 4, 6]:
            for exp_seed in [0, 1, 2]:
                if model_batch_size == 2 and exp_seed == 0:
                    continue
                yield {
                    "model.batch_size": model_batch_size,
                    "exp.seed": exp_seed,
                }
    ```
- When: `python sweep.py ... --sweep mysweep.my_sweep`
- Then: 等同於
    ```python
    for model_batch_size in [2, 4, 6]:
        for exp_seed in [0, 1, 2]:
            if model_batch_size == 2 and exp_seed == 0:
                    continue
            config = parser.parse_args(sys.argv[1:] + [
                "--args",
                f"model.batch_size={model_batch_size}",
                f"exp.seed={exp_seed}",
            ])
            experiment = config.exp.realize()
            experiment.run(**config.run.kwargs)
    ```