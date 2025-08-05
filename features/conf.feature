Feature: 自動根據物件建立 Command line interface
    
    Scenario: 利用你的 function 或 method 或 class 自動擴充 CLI
        Given 任何 function 或 method 或 class
            """
            ```python
            # function
            def my_function():...
            
            # instance method
            def my_method(self):...

            # class method
            def my_class_method(cls):...

            # class
            class MyClass:
                def __init__(self,):...
                    
            ```
            """


    Scenario: fff
        """
        
        """

        Given I have a configured twinconf project
            """
            ```python
            class OldestParent:
                def __init__(
                    self,
                    d: bool = True,
                ): ...

            class GrandParent(OldestParent):
                def __init__(
                    self,
                    a: int = 1,
                    b: str = "2",
                    c: float = 3.0,
                    **kwargs,
                ):
                    super().__init__(
                        d=True,
                        **kwargs
                    )

            class Parent(GrandParent):
                def __init__(
                    self,
                    a: int = 1,
                    b: str = "2",
                    c: float = 3.0,
                    **kwargs,
                ):
                    super().__init__(
                        )
            ```
            """
        When I run the twinconf command
            
        Then I should see the expected output