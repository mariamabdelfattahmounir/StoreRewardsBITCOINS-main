4// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract StoreRewardsV2 {
    
    string public coinName = "Reward Point Coin";
    string public coinSymbol = "RPC";
    uint8 public coinDecimals = 18;
    
    address public admin;
    uint256 public totalCoinSupply;
    
    mapping(address => uint256) public coinBalanceOf;
    mapping(address => mapping(address => uint256)) public coinAllowance;
    
    // Coin Events
    event CoinMinted(address indexed to, uint256 amount);
    event CoinTransferred(address indexed from, address indexed to, uint256 amount);
    event CoinApproved(address indexed owner, address indexed spender, uint256 amount);
    
    // Store Events
    event RewardItemAdded(uint256 indexed itemId, string name, uint256 pointsCost);
    event RewardItemUpdated(uint256 indexed itemId, string newName, uint256 newPointsCost);
    event RewardPurchased(address indexed user, uint256 indexed itemId, string itemName, uint256 pointsSpent);
    event UserRegistered(address indexed user, string name);
    event ContractPaused(address indexed admin);
     event ContractResumed(address indexed admin);
    event OwnershipTransferred(address indexed oldAdmin, address indexed newAdmin);
    
    struct RewardItem {
        uint256 id;
        string name;
        uint256 pointsCost;
        uint256 quantityAvailable;
        bool isActive;
    }
    
    mapping(uint256 => RewardItem) public rewardItems;
    mapping(address => string) public userNames;
    
    uint256 public nextItemId;
    uint256 public totalTransactions;
    bool public paused;
    
    modifier onlyAdmin() {
        require(msg.sender == admin, "Access denied: Only admin can call this");
        _;
    }
    
    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }
    
    constructor() {
        admin = msg.sender;
        paused = false;
        nextItemId = 1;
        totalTransactions = 0;
        totalCoinSupply = 0;
    }
    
    // =========================
    // ERC20-like Functions
    // =========================
    
    function mintCoins(address _to, uint256 _amount) external onlyAdmin {
        require(_to != address(0), "Cannot mint to zero address");
        require(_amount > 0, "Amount must be > 0");
        
        coinBalanceOf[_to] += _amount;
        totalCoinSupply += _amount;
        
        emit CoinMinted(_to, _amount);
        emit CoinTransferred(address(0), _to, _amount);
    }
    
    function transferCoins(address _to, uint256 _amount) external whenNotPaused returns (bool) {
        require(_to != address(0), "Invalid address");
        require(coinBalanceOf[msg.sender] >= _amount, "Insufficient balance");
        require(_amount > 0, "Amount must be > 0");
        
        coinBalanceOf[msg.sender] -= _amount;
        coinBalanceOf[_to] += _amount;
        
        emit CoinTransferred(msg.sender, _to, _amount);
        return true;
    }
    
    function approveCoinSpender(address _spender, uint256 _amount) external returns (bool) {
        require(_spender != address(0), "Cannot approve zero address");
        
        coinAllowance[msg.sender][_spender] = _amount;
        emit CoinApproved(msg.sender, _spender, _amount);
        return true;
    }
    
    function transferCoinsFrom(address _from, address _to, uint256 _amount) external returns (bool) {
        require(_to != address(0), "Invalid address"); 
        require(_amount > 0, "Amount must be > 0");
        require(coinBalanceOf[_from] >= _amount, "Insufficient balance");
        require(coinAllowance[_from][msg.sender] >= _amount, "Insufficient allowance");

        coinBalanceOf[_from] -= _amount;
        coinBalanceOf[_to] += _amount;
        coinAllowance[_from][msg.sender] -= _amount;

        emit CoinTransferred(_from, _to, _amount);
        return true;
    }
    
    function getCoinBalance(address _user) external view returns (uint256) {
        return coinBalanceOf[_user];
    }
    
    // =========================
    // Store Functions
    // =========================
    
    function addRewardItem(
        string memory _name,
        uint256 _pointsCost,
        uint256 _quantityAvailable
    ) external onlyAdmin whenNotPaused {
        
        require(bytes(_name).length > 0, "Name cannot be empty");
        require(_pointsCost > 0, "Points cost must be > 0");
        require(_quantityAvailable > 0, "Quantity must be > 0");
        
        rewardItems[nextItemId] = RewardItem({
            id: nextItemId,
            name: _name,
            pointsCost: _pointsCost,
            quantityAvailable: _quantityAvailable,
            isActive: true
        });
        
        emit RewardItemAdded(nextItemId, _name, _pointsCost);
        nextItemId++;
    }
    
    function updateRewardItem(
        uint256 _itemId,
        string memory _newName,
        uint256 _newPointsCost,
        uint256 _newQuantity,
        bool _isActive
    ) external onlyAdmin whenNotPaused {
        
        require(_itemId > 0 && _itemId < nextItemId, "Item does not exist");
        require(bytes(_newName).length > 0, "Name cannot be empty");
        require(_newPointsCost > 0, "Points cost must be > 0");
        
        RewardItem storage item = rewardItems[_itemId];
        
        item.name = _newName;
        item.pointsCost = _newPointsCost;
        item.quantityAvailable = _newQuantity;
        item.isActive = _isActive;
        
        emit RewardItemUpdated(_itemId, _newName, _newPointsCost);
    }
    
    function batchAddOrUpdateItems(
        string[] memory _names,
        uint256[] memory _costs,
        uint256[] memory _qtys
    ) external onlyAdmin whenNotPaused {
        
        require(_names.length == _costs.length && _costs.length == _qtys.length, "Arrays length mismatch");
        require(_names.length > 0, "Empty batch");
        
        for (uint256 i = 0; i < _names.length; i++) {
            
            require(bytes(_names[i]).length > 0, "Name cannot be empty");
            require(_costs[i] > 0, "Cost must be > 0");
            require(_qtys[i] > 0, "Quantity must be > 0");
            
            rewardItems[nextItemId] = RewardItem({
                id: nextItemId,
                name: _names[i],
                pointsCost: _costs[i],
                quantityAvailable: _qtys[i],
                isActive: true
            });
            
            emit RewardItemAdded(nextItemId, _names[i], _costs[i]);
            nextItemId++;
        }
    }
    
    
    function deactivateItem(uint256 _itemId) external onlyAdmin {
        require(_itemId > 0 && _itemId < nextItemId, "Invalid ID");
        rewardItems[_itemId].isActive = false;
    }
    
    function pause() external onlyAdmin {
        require(!paused, "Already paused");
        paused = true;
        emit ContractPaused(msg.sender);
    }
    
    function resume() external onlyAdmin {
        require(paused, "Not paused");
        paused = false;
        emit ContractResumed(msg.sender);
    }
    
    function transferOwnership(address _newAdmin) external onlyAdmin {
        require(_newAdmin != address(0), "New admin cannot be zero");
        require(_newAdmin != admin, "Must be different");
        
        address oldAdmin = admin;
        admin = _newAdmin;
        emit OwnershipTransferred(oldAdmin, _newAdmin);
    }
    
    // =========================
    // User Functions
    // =========================
    
    function registerUser(string memory _name) external whenNotPaused {
        require(bytes(_name).length > 0, "Name cannot be empty");
        require(bytes(userNames[msg.sender]).length == 0, "Already registered");
        
        userNames[msg.sender] = _name;
        emit UserRegistered(msg.sender, _name);
        totalTransactions++;
    }
    
    function purchaseRewardItem(uint256 _itemId) external whenNotPaused {
        
        require(_itemId > 0 && _itemId < nextItemId, "Item does not exist"); // ✅ fix
        require(bytes(userNames[msg.sender]).length > 0, "User not registered");
        require(rewardItems[_itemId].isActive, "Item not available");
        require(rewardItems[_itemId].quantityAvailable > 0, "Out of stock");
        require(coinBalanceOf[msg.sender] >= rewardItems[_itemId].pointsCost, "Insufficient coins");
        
        coinBalanceOf[msg.sender] -= rewardItems[_itemId].pointsCost;
        rewardItems[_itemId].quantityAvailable--;
        
        emit RewardPurchased(
            msg.sender,
            _itemId,
            rewardItems[_itemId].name,
            rewardItems[_itemId].pointsCost
        );
        
        totalTransactions++;
    }
    
    // =========================
    // View Functions
    // =========================
    
    function getAdmin() external view returns (address) {
        return admin;
    }
    
    function getContractPaused() external view returns (bool) {
        return paused;
    }
    
    function getTotalRewardItems() external view returns (uint256) {
        return nextItemId - 1;
    }
    
    function getTotalTransactions() external view returns (uint256) {
        return totalTransactions;
    }
    
    function getTotalMintedCoins() external view returns (uint256) {
        return totalCoinSupply;
    }
    
    function getUserName(address _user) external view returns (string memory) {
        return userNames[_user];
    }
    
    function getRewardItem(uint256 _itemId) external view returns (
        uint256 id,
        string memory name,
        uint256 pointsCost,
        uint256 quantityAvailable,
        bool isActive
    ) {
        RewardItem memory item = rewardItems[_itemId];
        return (item.id, item.name, item.pointsCost, item.quantityAvailable, item.isActive);
    }
}